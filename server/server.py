import sqlite3
import json
import requests
import datetime
import polyline
import os
from pprint import pprint
from peewee import *
from flask import Flask, render_template, request
from flask_cors import CORS
from stravalib.client import Client

client = Client()

db = SqliteDatabase('strava.db')
app = Flask(__name__)
CORS(app)

STRAVA_API_KEY = os.getenv("STRAVA_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

BEST_SEGMENTS = [1535164, 1658714, 15765875, 2474266, 2019489, 8199567]


class Trail(Model):
    strava_segment_id = IntegerField(index=True)
    strava_segment_name = TextField()
    trail_name = TextField()
    city = TextField(null=True)
    state = TextField(null=True)
    athlete_count = IntegerField()
    effort_count = IntegerField()
    distance = FloatField()
    average_grade = FloatField()
    maximum_grade = FloatField()
    elevation_high = FloatField()
    elevation_low = FloatField()
    total_elevation_gain = FloatField(null=True)
    polyline = TextField(null=True)
    geojson = TextField(null=True)

    @staticmethod
    def serialize(trail):
        return {
            "strava_segment_id": trail.strava_segment_id,
            "strava_segment_name": trail.strava_segment_name,
            "trail_name": trail.trail_name,
            "city": trail.city,
            "state": trail.state,
            "athlete_count": trail.athlete_count,
            "effort_count": trail.effort_count,
            "distance": trail.distance,
            "average_grade": trail.average_grade,
            "maximum_grade": trail.maximum_grade,
            "elevation_high": trail.elevation_high,
            "elevation_low": trail.elevation_low,
            "total_elevation_gain": trail.total_elevation_gain,
            "polyline": trail.polyline,
            "geojson": trail.geojson
        }

    class Meta:
        database = db


class Effort(Model):
    trail_id = IntegerField()
    athlete_name = TextField()
    start_date = DateTimeField()
    start_date_local = TextField()
    moving_time = IntegerField()
    elapsed_time = IntegerField()
    rank = IntegerField()

    @staticmethod
    def serialize(effort):
        return {
            "trail_id": effort.trail_id,
            "athlete_name": effort.athlete_name,
            "start_date": effort.start_date,
            "start_date_local": effort.start_date_local,
            "moving_time": effort.moving_time,
            "elapsed_time": effort.elapsed_time,
            "rank": effort.rank
        }

    class Meta:
        database = db


def init_segment(segmentId):
    segmentId = str(segmentId)
    print('\n > #' + segmentId + ' STARTING!')
    segment = Trail.get_or_none(Trail.strava_segment_id == segmentId)

    if segment is None:
        print('   ? segment not found in db, fetching segment from strava api...')

        r = requests.get(
            'https://www.strava.com/api/v3/segments/' + segmentId,
            headers={ 'Authorization': 'Bearer ' + STRAVA_API_KEY }
        )
        if r.status_code == 200:
            data = r.json()

            geojson = get_geojson(data['id'])
            geojson = attach_elevation(geojson)

            createdTrail = Trail.create(
                strava_segment_id=data['id'], strava_segment_name=data['name'], trail_name=data['name'],
                city=data['city'], state=data['state'], athlete_count=data['athlete_count'], effort_count=data['effort_count'],
                distance=data['distance'], average_grade=data['average_grade'], maximum_grade=data['maximum_grade'],
                elevation_high=data['elevation_high'], elevation_low=data['elevation_low'],
                total_elevation_gain=data['total_elevation_gain'], polyline=data['map']['polyline'], geojson=geojson
            )

            print('   ✓ ' + createdTrail.strava_segment_name + ' segment inserted into db from Strava API')
            segment = createdTrail
        else:
            print('   X Error returned by Strava! ' + r.status_code)
            return None

    else:
        print('   ✓ segment found in db')

    init_segment_efforts(segmentId)
    return segment

def init_segment_efforts(segmentId):
    efforts = Effort.get_or_none(Effort.trail_id == segmentId)
    if efforts is None:
        print('      ? no efforts in db, fetching efforts from strava api...')
        get_efforts(segmentId, '')
        get_efforts(segmentId, 'this_year')
        get_efforts(segmentId, 'this_month')
        get_efforts(segmentId, 'this_week')

def get_efforts(segmentId, date_range):
    r = requests.get('https://www.strava.com/api/v3/segments/' + segmentId + '/leaderboard?gender=M&per_page=100&page=1&date_range=' + date_range, headers={'Authorization': 'Bearer ' + STRAVA_API_KEY})

    if r.status_code == 200:
        data = r.json()
        print('      ✓ got ' + str(len(data['entries'])) + ' EFFORTS '  + date_range)
        if len(data['entries']) > 0:
            for entry in data['entries']:
                entry.update({ 'trail_id': int(segmentId) })
            effortsToInsert = data['entries']
            # todo: trim duplicates
            Effort.insert_many(effortsToInsert).execute()

def get_geojson(segmentId):
    segmentId = str(segmentId)

    r = requests.get('https://www.strava.com/api/v3/segments/' + segmentId + '/streams', headers={'Authorization': 'Bearer ' + STRAVA_API_KEY})
    if r.status_code == 200:
        data = r.json()
        latlng = []
        for stream in data:
            if stream['type'] == 'latlng':
                latlngs = stream['data']

        lnglats = []
        for latlng in latlngs:
            lnglats.append([ latlng[1],latlng[0] ])

        feature = {'type': 'Feature'}

        feature['geometry'] = {
            'type': 'LineString',
            'coordinates': lnglats
        }

        feature['properties'] = { 'name': segmentId }

        return json.dumps(feature)

    else:
        return

def attach_elevation_r(coords, page=1):
    url = "http://dev.virtualearth.net/REST/v1/Elevation/List"
    start = (page-1)*50
    if page*50 > len(coords):
        end = len(coords)
    else:
        end = page*50

    print("        fetching " + str(start) + " to " + str(end))

    coordsString = ",".join(map(str, sum(coords[start:end], [])))

    request = requests.get(url+"?points="+coordsString+"&key="+BING_API_KEY)
    elevations = json.loads(request.text)['resourceSets'][0]['resources'][0]['elevations']

    for i in range(start,end):
        coords[i].append(elevations[i-start])

    if end == len(coords):
        return coords
    else:
        return attach_elevation_r(coords, page+1)

def attach_elevation(geojson):
    geojson = json.loads(geojson)
    coords = geojson['geometry']['coordinates']
    for i in range(0,len(coords)):
        coords[i].reverse()

    if len(coords) > 50:
        coords = attach_elevation_r(coords)

        for i in range(0,len(coords)):
            tmp = coords[i][0]
            coords[i][0] = coords[i][1]
            coords[i][1] = tmp

        geojson['geometry']['coordinates'] = coords
        return json.dumps(geojson)

    else:
        print("segment too short, skipping...")


if __name__ == "__main__":
    print("resetting DB")
    db.drop_tables([Trail, Effort])
    db.create_tables([Trail, Effort])
    db.close()
    print("populating DB")
    for i in range(len(BEST_SEGMENTS)):
        init_segment(BEST_SEGMENTS[i])


@app.route("/trails")
def get_trails():
    return json.dumps(list(Trail.select()), default=Trail.serialize)

@app.route("/trail/<segment_id>")
def get_trail(segment_id):
    trail = json.dumps(init_segment(segment_id), default=Trail.serialize)
    return trail

@app.route("/trail/<segment_id>/efforts")
def get_trail_efforts(segment_id):
    listOfEfforts = list(Effort.select().join(Trail, on=(Effort.trail_id == Trail.strava_segment_id)))
    return json.dumps(listOfEfforts, default=Effort.serialize)

@app.route("/trail/<segment_id>/efforts/dateRange/<date_start>/<date_end>")
def get_efforts_by_dateRange(segment_id, date_start, date_end):
    listOfEfforts = list(Effort.select().join(Trail, on=(Effort.trail_id == Trail.strava_segment_id)).where(Effort.start_date.between(date_start, date_end)))
    return json.dumps(listOfEfforts, default=Effort.serialize)

@app.route('/')
def base():
    return render_template('index.html')


















