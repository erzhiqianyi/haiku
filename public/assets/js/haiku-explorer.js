(() => {
    "use strict";

    const seasonColors = {
        春: "#a66f7f",
        夏: "#4f806b",
        秋: "#a56f3e",
        冬: "#667b8d",
        新年: "#986b67",
        余白: "#746f67"
    };

    function initSeasonWhispers() {
        const orbit = document.querySelector(".season-orbit");
        const container = document.querySelector("#season-whispers");
        const dataElement = document.querySelector("#kigo-season-data");
        if (!orbit || !container || !dataElement) {
            return;
        }

        let wordsBySeason;
        try {
            wordsBySeason = JSON.parse(dataElement.textContent);
        } catch (error) {
            return;
        }

        let activeSeason = document.body.dataset.currentSeason || "春";
        let lastWord = "";
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        const spawnWord = () => {
            const words = wordsBySeason[activeSeason] || [];
            if (!words.length) {
                return;
            }

            const candidates = words.filter((word) => word !== lastWord);
            const source = candidates.length ? candidates : words;
            const word = source[Math.floor(Math.random() * source.length)];
            lastWord = word;

            const angle = Math.random() * Math.PI * 2;
            const radius = 24 + (Math.random() * 18);
            const whisper = document.createElement("span");
            whisper.className = "season-whisper";
            if (Math.random() > 0.62) {
                whisper.classList.add("is-vertical");
            }
            whisper.textContent = word;
            whisper.style.left = `${50 + (Math.cos(angle) * radius)}%`;
            whisper.style.top = `${50 + (Math.sin(angle) * radius)}%`;
            whisper.style.fontSize = `${0.62 + (Math.random() * 0.34)}rem`;
            whisper.style.animationDuration = `${4.4 + (Math.random() * 2.2)}s`;
            container.appendChild(whisper);

            if (reducedMotion) {
                while (container.children.length > 1) container.firstElementChild.remove();
                return;
            }

            whisper.addEventListener("animationend", () => whisper.remove(), {once: true});
            while (container.children.length > 7) container.firstElementChild.remove();
        };

        const showSeason = (season) => {
            if (!wordsBySeason[season]) {
                return;
            }
            activeSeason = season;
            lastWord = "";
            container.replaceChildren();
            const initialCount = reducedMotion ? 1 : 4;
            for (let index = 0; index < initialCount; index += 1) {
                window.setTimeout(spawnWord, index * 240);
            }
        };

        document.querySelectorAll("[data-season-link]").forEach((link) => {
            link.addEventListener("click", () => showSeason(link.dataset.seasonLink));
        });

        const seasonObserver = new MutationObserver(() => {
            const season = document.body.dataset.currentSeason;
            if (season && season !== activeSeason) {
                showSeason(season);
            }
        });
        seasonObserver.observe(document.body, {attributes: true, attributeFilter: ["data-current-season"]});

        showSeason(activeSeason);
        if (!reducedMotion) {
            window.setInterval(spawnWord, 1350);
        }
    }

    function initKigoExplorer() {
        const status = document.querySelector("#kigo-search-status");
        const cards = [...document.querySelectorAll(".kigo-card")];
        const sections = [...document.querySelectorAll("[data-season-section]")];
        const seasonLinks = [...document.querySelectorAll("[data-season-link]")];
        const currentSeasonEn = document.querySelector("#kigo-current-season-en");
        const currentSeasonName = document.querySelector("#kigo-current-season-name");
        const currentSeasonMeta = document.querySelector("#kigo-current-season-meta");

        if (!status || !cards.length || !sections.length || !seasonLinks.length) {
            return;
        }

        const seasons = sections.map((section) => section.dataset.seasonSection);
        const seasonForDate = (date) => {
            const monthDay = (date.getMonth() + 1) * 100 + date.getDate();
            if (monthDay >= 204 && monthDay <= 505) return "春";
            if (monthDay >= 506 && monthDay <= 807) return "夏";
            if (monthDay >= 808 && monthDay <= 1106) return "秋";
            return "冬";
        };
        const currentTokyoSeason = () => {
            const parts = new Intl.DateTimeFormat("en-CA", {
                timeZone: "Asia/Tokyo",
                year: "numeric",
                month: "2-digit",
                day: "2-digit"
            }).formatToParts(new Date());
            const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
            return seasonForDate(new Date(`${values.year}-${values.month}-${values.day}T00:00:00`));
        };
        const seasonFromHash = () => {
            const decoded = decodeURIComponent(window.location.hash.replace(/^#season-/, ""));
            if (seasons.includes(decoded)) {
                return decoded;
            }
            const currentSeason = currentTokyoSeason();
            return seasons.includes(currentSeason) ? currentSeason : seasons[0];
        };
        const showSeason = (season, updateHash = true) => {
            if (!seasons.includes(season)) {
                return;
            }
            document.body.dataset.currentSeason = season;
            sections.forEach((section) => {
                section.hidden = section.dataset.seasonSection !== season;
            });
            seasonLinks.forEach((link) => {
                const selected = link.dataset.seasonLink === season;
                link.setAttribute("aria-selected", String(selected));
                link.setAttribute("aria-current", selected ? "true" : "false");
                link.tabIndex = selected ? 0 : -1;
            });
            const activeCards = cards.filter((card) => card.closest("[data-season-section]")?.dataset.seasonSection === season);
            status.textContent = `${activeCards.length}の季語`;
            const activeSection = sections.find((section) => section.dataset.seasonSection === season);
            if (activeSection && currentSeasonEn && currentSeasonName && currentSeasonMeta) {
                currentSeasonEn.textContent = activeSection.dataset.seasonEnglish || "";
                currentSeasonName.textContent = season;
                currentSeasonMeta.textContent = `${activeSection.dataset.seasonPhrase || ""}・${activeSection.dataset.seasonCount || activeCards.length}句`;
            }
            if (updateHash) {
                window.history.pushState(null, "", `#season-${encodeURIComponent(season)}`);
            }
        };

        seasonLinks.forEach((link) => {
            link.addEventListener("click", (event) => {
                event.preventDefault();
                const scrollPosition = {x: window.scrollX, y: window.scrollY};
                showSeason(link.dataset.seasonLink);
                window.requestAnimationFrame(() => {
                    window.scrollTo(scrollPosition.x, scrollPosition.y);
                });
            });
        });

        window.addEventListener("popstate", () => showSeason(seasonFromHash(), false));
        showSeason(seasonFromHash(), false);
    }

    function initLocationListExplorer() {
        const input = document.querySelector("#location-search");
        const status = document.querySelector("#location-search-status");
        const rows = [...document.querySelectorAll("[data-location-search]")];
        const groups = [...document.querySelectorAll("[data-location-group]")];

        if (!input || !status || !rows.length) {
            return;
        }

        const normalize = (value) => value.normalize("NFKC").toLocaleLowerCase("ja").trim();
        const filterLocations = () => {
            const query = normalize(input.value);
            let visibleCount = 0;

            rows.forEach((row) => {
                const matches = !query || normalize(row.dataset.locationSearch || "").includes(query);
                row.hidden = !matches;
                if (matches) visibleCount += 1;
            });

            groups.forEach((group) => {
                group.hidden = !group.querySelector("[data-location-search]:not([hidden])");
            });

            status.textContent = query ? `${visibleCount}の場所が見つかりました` : `${rows.length}の場所`;
        };

        input.addEventListener("input", filterLocations);
    }

    function popupContent(location) {
        const wrapper = document.createElement("div");
        wrapper.className = "map-popup";

        const heading = document.createElement("a");
        heading.href = location.url;
        heading.innerHTML = window.HaikuReadings
            ? window.HaikuReadings.formatRubyValue(location.nameRuby)
            : escapeHtml(location.name);

        const meta = document.createElement("span");
        meta.textContent = `${location.count}句${location.precision === "area" ? "・おおよその位置" : ""}`;

        const preview = document.createElement("p");
        preview.innerHTML = window.HaikuReadings && Array.isArray(location.previewRuby)
            ? location.previewRuby.map(window.HaikuReadings.formatRubyValue).join('<span aria-hidden="true">／</span>')
            : escapeHtml(location.preview);

        wrapper.append(heading, meta, preview);
        return wrapper;
    }

    function initLocationMap() {
        const mapElement = document.querySelector("#haiku-map");
        const dataElement = document.querySelector("#location-map-data");
        const fallback = document.querySelector("#map-fallback");

        if (!mapElement || !dataElement) {
            return;
        }

        if (!window.L) {
            mapElement.hidden = true;
            if (fallback) {
                fallback.hidden = false;
            }
            return;
        }

        let mapData;
        try {
            mapData = JSON.parse(dataElement.textContent);
        } catch (error) {
            mapElement.hidden = true;
            if (fallback) {
                fallback.hidden = false;
            }
            return;
        }
        const prefectures = Array.isArray(mapData.prefectures) ? mapData.prefectures : [];
        if (!prefectures.length) {
            mapElement.hidden = true;
            if (fallback) {
                fallback.hidden = false;
            }
            return;
        }

        const map = window.L.map(mapElement, {
            scrollWheelZoom: false,
            zoomControl: true
        });

        const tiles = window.L.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener noreferrer">国土地理院</a>'
        });
        tiles.addTo(map);

        let tileErrors = 0;
        tiles.on("tileerror", () => {
            tileErrors += 1;
            if (tileErrors >= 8 && fallback) {
                fallback.hidden = false;
            }
        });

        const escapeHtml = (value) => value.replace(/[&<>'"]/g, (character) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "'": "&#39;",
            '"': "&quot;"
        })[character]);

        let placeLayer;
        const makeMarker = (location) => {
            const color = seasonColors[location.season] || seasonColors["余白"];
            const marker = window.L.marker([location.lat, location.lng], {
                title: `${location.name}、${location.count}句`,
                poemCount: location.count,
                icon: window.L.divIcon({
                    className: "haiku-place-marker",
                    html: `<span class="place-marker-dot" style="--marker-color:${color}"><strong>${location.count}</strong><small>句</small></span><span class="place-marker-name">${window.HaikuReadings ? window.HaikuReadings.formatRubyValue(location.nameRuby) : escapeHtml(location.name)}</span>`,
                    iconSize: [96, 58],
                    iconAnchor: [48, 29]
                })
            });
            marker.bindPopup(popupContent(location), {maxWidth: 280, offset: [0, -16]});
            return marker;
        };

        const prefectureName = document.querySelector("#map-prefecture-name");
        const prefectureCount = document.querySelector("#map-prefecture-count");
        const prefectureButtons = [...document.querySelectorAll("[data-map-prefecture]")];

        const renderPrefecture = (prefectureNameValue, animate = true) => {
            const prefecture = prefectures.find((item) => item.name === prefectureNameValue);
            const visibleLocations = prefecture ? prefecture.locations : [];
            if (!visibleLocations.length) {
                return;
            }
            if (placeLayer) {
                map.removeLayer(placeLayer);
            }

            const clusterOptions = {
                showCoverageOnHover: false,
                spiderfyOnMaxZoom: true,
                maxClusterRadius: 62,
                iconCreateFunction: (cluster) => {
                    const poemCount = cluster.getAllChildMarkers().reduce((sum, marker) => sum + marker.options.poemCount, 0);
                    return window.L.divIcon({
                        className: "haiku-place-cluster",
                        html: `<span><strong>${poemCount}</strong><small>句</small></span>`,
                        iconSize: [64, 64]
                    });
                }
            };
            placeLayer = window.L.markerClusterGroup ? window.L.markerClusterGroup(clusterOptions) : window.L.layerGroup();
            const markers = visibleLocations.map(makeMarker);
            markers.forEach((marker) => placeLayer.addLayer(marker));
            placeLayer.addTo(map);

            const bounds = window.L.latLngBounds(visibleLocations.map((location) => [location.lat, location.lng]));
            if (visibleLocations.length === 1) {
                map.setView(bounds.getCenter(), 12, {animate});
            } else if (bounds.isValid()) {
                map.fitBounds(bounds.pad(0.18), {maxZoom: 13, animate});
            }

            const total = visibleLocations.reduce((sum, location) => sum + location.count, 0);
            if (prefectureName) {
                prefectureName.textContent = prefectureNameValue;
            }
            if (prefectureCount) {
                prefectureCount.textContent = `${total}句`;
            }
            prefectureButtons.forEach((button) => {
                button.setAttribute("aria-pressed", String(button.dataset.mapPrefecture === prefectureNameValue));
            });
        };

        prefectureButtons.forEach((button) => {
            button.addEventListener("click", () => renderPrefecture(button.dataset.mapPrefecture));
        });

        renderPrefecture(mapData.defaultPrefecture, false);
        window.requestAnimationFrame(() => map.invalidateSize());
        window.setTimeout(() => map.invalidateSize(), 180);
    }

    document.addEventListener("DOMContentLoaded", () => {
        initKigoExplorer();
        initLocationListExplorer();
        initSeasonWhispers();
        initLocationMap();
    });
})();
