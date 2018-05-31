const m = require("mithril")
const Trails = require("../models/Trails")
const metersToMiles = 1609.34;
const metersToFeet = 0.3048;

const TrailInfo = {
	view: function(data) {
		let trailData = data.attrs;
		let cityAndState = trailData.city + " " + trailData.state;
		let distanceAscentDescent = (trailData.distance / metersToMiles).toFixed(2) + " mi / " + 
			(trailData.total_elevation_gain / metersToFeet).toFixed(2) + " ft / " +
			((trailData.elevation_high - trailData.elevation_low) / metersToFeet).toFixed(2) + " ft";

		return m("div#trail-info", [
			m("div.trail-info-section", [
				m("div.trail-info-section-header", "Segment Name"),
				m("div.trail-info-section-content", trailData.trail_name),
			]),
			m("div.trail-info-section", [
				m("div.trail-info-section-header", "Segment Location"),
				m("div.trail-info-section-content", cityAndState),
			]),
			m("div.trail-info-section", [
				m("div.trail-info-section-header", "Distance / Ascent / Descent"),
				m("div.trail-info-section-content", distanceAscentDescent),
			]),
		]);
	}
}

const Trail = {
	view: (data) => m("section", [ m('h3', data.attrs.trail_name), m(TrailInfo, data.attrs) ])
};

const renderTrail = function(trail_name) {
	let i = Trails.list.findIndex((trail) => trail.trail_name == trail_name);
	let trailData = Trails.list[i];
	let geojson = JSON.parse(trailData.geojson);
	let center = [
		geojson.geometry.coordinates[Math.floor(geojson.geometry.coordinates.length / 2)][1],
		geojson.geometry.coordinates[Math.floor(geojson.geometry.coordinates.length / 2)][0]
	];
	document.querySelector('#map').style.visibility = 'visible';

	trailLayerGroup.clearLayers();
	el.clear();
	map.setView(center, 12);

	L.geoJson(geojson,{
	    onEachFeature: el.addData.bind(el)
	}).addTo(trailLayerGroup);

	// todo: create a RIDEABILITY score and a color indicator RED YELLOW GREEN depending on recent traffic
	// RECENT TRAFFIC:  # of riders in past 7 days
	// RATE OF IMPROVEMENT MEASURE:  (# of riders in past 7 days)-(# of riders previous 7 days)
	// RIDEABILITY SCORE:   RECENT TRAFFIC + RATE of IMPROVEMENT + % RECENTLY COMPLETING IN REASONABLE TIME   (Scaled 0-100 where 0 is nobody riding successfully, 100 is open, fast, popular)

	return m.render(document.querySelector('#trail'), m(Trail, trailData))
}

const TrailList = {
	oninit: Trails.loadList,
	view: function() {
		if (Trails.list.length > 0) {
			const oninput = m.withAttr("value", renderTrail);
			const createOption = ({ trail_name }) => m("option", { value: trail_name }, trail_name);
			return m("select",
				{ id: "trail-list", className: "form-control", oninput },
				[ m("option", { selected: "true", value: "", disabled: "true", hidden: "true" }, "Choose a Trail..."),
					Trails.list.map(createOption) ]);
		}
		else {
			return
		}
	}
};

module.exports = TrailList