const m = require("mithril")

const Trails = {
    list: [],
    loadList: () =>
        m.request({ method: "GET", url: "http://127.0.0.1:5000/trails" })
            .then((trails) => { Trails.list = trails })
};

module.exports = Trails
