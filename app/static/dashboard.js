window.onload = async function () {
    const propsResp = await fetch('/api/props');
    const props = await propsResp.json();
    const propsList = document.getElementById('props-list');
    propsList.innerHTML = '';
    props.forEach((prop) => {
        propsList.innerHTML += `
          <div class="prop-item" data-prop-id="${prop.prop_id}">
            <div class="prop-info">
              <div class="prop-name">${prop.player_name}</div>
              <img class="prop-team-logo" src="/static/team_logos/${prop.player_team_id}.svg" alt="${prop.player_team_abbr} logo"/>
              <span class="prop-team-abbr">${prop.player_team_abbr}</span>
              <span class="prop-type">${prop.prop_type}</span>
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

    document.getElementById('pitcher-headshot').src = pitcher.headshot || '/static/headshots/placeholder.png';
    document.getElementById('pitcher-team-logo').src = (pitcher.team && pitcher.team.logo) || '';
    document.getElementById('pitcher-name').textContent = pitcher.name || '';

    renderStatsCard(batter.season_stats, batter.career_stats, true);
    renderStatsCard(pitcher.season_stats, pitcher.career_stats, false);

    document.getElementById('prop-type').textContent = prop.type || '';
    document.getElementById('prop-odds').textContent = `Odds: ${prop.odds || ''}`;
}

function renderStatsCard(season, career, isBatter) {
    const box = document.getElementById(isBatter ? 'batter-stats' : 'pitcher-stats');
    const seasonKeys = isBatter ? ['avg', 'hr', 'obp', 'ops', 'rbi'] : ['era', 'whip', 'k9', 'bb9'];
    const seasonLabels = isBatter ? ['AVG', 'HR', 'OBP', 'OPS', 'RBI'] : ['ERA', 'WHIP', 'K9', 'BB9'];
    const careerKeys = seasonKeys;
    const careerLabels = seasonLabels;
    let html = '';

    // Season
    html += `<div class="stats-section-title">Season</div>`;
    for (let i = 0; i < seasonKeys.length; i += 2) {
        html += `<div><span class="stat-label">${seasonLabels[i]}</span> <span class="stat-value">${season && season[seasonKeys[i]] !== undefined ? season[seasonKeys[i]] : '-'}</span></div>`;
        if (seasonKeys[i+1]) {
            html += `<div><span class="stat-label">${seasonLabels[i+1]}</span> <span class="stat-value">${season && season[seasonKeys[i+1]] !== undefined ? season[seasonKeys[i+1]] : '-'}</span></div>`;
        }
    }
    // Career
    html += `<div class="stats-section-title">Career</div>`;
    for (let i = 0; i < careerKeys.length; i += 2) {
        html += `<div><span class="stat-label">${careerLabels[i]}</span> <span class="stat-value">${career && career[careerKeys[i]] !== undefined ? career[careerKeys[i]] : '-'}</span></div>`;
        if (careerKeys[i+1]) {
            html += `<div><span class="stat-label">${careerLabels[i+1]}</span> <span class="stat-value">${career && career[careerKeys[i+1]] !== undefined ? career[careerKeys[i+1]] : '-'}</span></div>`;
        }
    }
    box.innerHTML = html;
}
