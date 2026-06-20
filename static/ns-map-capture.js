(function() {
    var orig = L.map;
    L.map = function() {
        var m = orig.apply(this, arguments);
        window.__ns_map = m;

        var origFire = m.fire;
        m.fire = function(type, data) {
            if (type === 'draw:created' && data && data.layer) {
                var realLayer = data.layer;
                data.layer = { _latlngs: realLayer._latlngs };
                try {
                    origFire.call(this, type, data);
                } catch(err) {}
                realLayer.addTo(this);
                return this;
            }
            return origFire.apply(this, arguments);
        };

        return m;
    };
    L.map.prototype = orig.prototype;
})();
