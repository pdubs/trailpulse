const m = require("mithril");

const TrailList = require("./views/TrailList");

const $trails = document.querySelector('#trails');

const App = {
	view: () => m("section", [
		m("h1.header", "trail pulse"),
		m(TrailList),
		m("hr")
	])
};

m.mount($trails, App)