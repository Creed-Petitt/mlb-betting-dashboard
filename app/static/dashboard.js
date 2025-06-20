// Fetch and display all props on page load
window.onload = async function () {
    const propsResp = await fetch('/api/props');
    const props = await propsResp.json();
    const propsList = document.getElementById('props-list');
    propsList.innerHTML = '';
    props.forEach((prop) => {
        let headshotPath = (prop.player_espn_id && !isNaN(prop.player_espn_id))
            ? `/static/headshots/${prop.player_espn_id}.png`
            : '/static/headshots/placeholder.png';
        propsList.innerHTML += `
            <div class="prop-item" data-prop-id="${prop.prop_id}">
                <div class="prop-headshot-wrap">
                    <img class="prop-headshot" src="${headshotPath}">
                </div>
                <div class="prop-info">
                    <div class="prop-name">${prop.player_name}</div>
                    <div class="prop-team">
                        <img class="prop-team-logo" src="/static/team_logos/${prop.player_team_id}.svg" />
                        <span class="prop-team-abbr">${prop.player_team_abbr}</span>
                        <span class="prop-type">${prop.prop_type}</span>
                    </div>
                </div>
                <div class="prop-odds">${prop.odds}</div>
            </div>
        `;
    });
    document.querySelectorAll('.prop-item').forEach(el => {
        el.onclick = () => loadMatchup(el.getAttribute('data-prop-id'));
    });
    if (props.length > 0) {
        loadMatchup(props[0].prop_id);
    }
};

async function loadMatchup(propId) {
    const resp = await fetch(`/api/prop/${propId}/matchup`);
    const data = await resp.json();

    const batter = (data && data.batter) || {};
    const pitcher = (data && data.pitcher) || {};
    const prop = (data && data.prop) || {};

    document.getElementById('batter-headshot').src = batter.headshot || '/static/headshots/placeholder.png';
    document.getElementById('batter-team-logo').src = (batter.team && batter.team.logo) || '';
    document.getElementById('batter-name').textContent = batter.name || '';
    document.getElementById('batter-stats').innerHTML = renderStats(batter.season_stats, batter.career_stats);

    document.getElementById('pitcher-headshot').src = pitcher.headshot || '/static/headshots/placeholder.png';
    document.getElementById('pitcher-team-logo').src = (pitcher.team && pitcher.team.logo) || '';
    document.getElementById('pitcher-name').textContent = pitcher.name || '';
    document.getElementById('pitcher-stats').innerHTML = renderStats(pitcher.season_stats, pitcher.career_stats);

    document.getElementById('prop-type').textContent = prop.type || '';
    document.getElementById('prop-odds').textContent = `Odds: ${prop.odds || ''}`;
}

function renderStats(season, career) {
    let html = '';
    if (season && Object.keys(season).length) {
        html += `<div><b>Season:</b> ${formatStats(season)}</div>`;
    }
    if (career && Object.keys(career).length) {
        html += `<div><b>Career:</b> ${formatStats(career)}</div>`;
    }
    if (!html) html = `<div>No stats found.</div>`;
    return html;
}

function formatStats(stats) {
    return Object.entries(stats || {})
        .map(([k, v]) => `${k.toUpperCase()}: ${v}`)
        .join(' | ');
}
