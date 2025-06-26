let propsData = [];
let teamsData = [];
let selectedPropId = null;
let currentFilters = {
    team: '',
    propType: '',
    game: ''
};

document.addEventListener('DOMContentLoaded', function() {
    loadInitialData();
});

async function loadInitialData() {
    showLoading(true);
    try {
        // Load props and teams
        await Promise.all([
            loadProps(),
            loadTeams()
        ]);
        
        // Initialize filters
        initializeFilters();
        
        // Render props
        renderProps(propsData);
        updatePropsCount(propsData.length);
        
        hideError();
    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load data. Please try again later.');
    } finally {
        showLoading(false);
    }
}

async function loadTeams() {
    try {
        const response = await fetch('/api/teams');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        teamsData = await response.json();
    } catch (error) {
        console.error('Error loading teams:', error);
        // Don't throw error for teams - it's not critical
    }
}

async function loadProps() {
    try {
        const response = await fetch('/api/props?per_page=500');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Deduplicate props - keep only the most recent prop per player
        const propsMap = new Map();
        data.results.forEach(prop => {
            const key = `${prop.player_id}-${prop.prop_type}`;
            if (!propsMap.has(key) || new Date(prop.date) > new Date(propsMap.get(key).date)) {
                propsMap.set(key, prop);
            }
        });
        
        propsData = Array.from(propsMap.values());
        window.propsData = propsData; // For backward compatibility
        
    } catch (error) {
        console.error('Error loading props:', error);
        throw error;
    }
}

function renderProps(props) {
    const container = document.getElementById('props-container');
    
    if (!props || props.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No props available</h3>
                <p>Try adjusting your filters or check back later for new props.</p>
            </div>
        `;
        return;
    }
    
    const grid = document.createElement('div');
    grid.className = 'props-grid';
    
    props.forEach(prop => {
        const card = createPropCard(prop);
        grid.appendChild(card);
    });
    
    container.innerHTML = '';
    container.appendChild(grid);
}

function createPropCard(prop) {
    const card = document.createElement('div');
    card.className = 'prop-card';
    card.dataset.propId = prop.prop_id;
    
    // For "To Record A Hit" props, the line is typically 0.5
    const displayLine = prop.prop_type === 'To Record A Hit' ? '0.5' : (prop.line || 'N/A');
    
    card.innerHTML = `
        <div class="prop-header">
            <img class="player-headshot" 
                 src="/static/headshots/${prop.player_espn_id || 'placeholder'}.png" 
                 alt="${prop.player_name}"
                 onerror="this.src='/static/headshots/placeholder.svg'">
            <div class="player-info">
                <h3>${prop.player_name}</h3>
                <p class="player-meta">${prop.position || 'N/A'} • ${prop.player_team_abbr}</p>
            </div>
            <img class="team-logo-small" 
                 src="/static/team_logos/${prop.player_team_id}.svg" 
                 alt="${prop.player_team_abbr}"
                 onerror="this.style.display='none'">
        </div>
        
        <div class="prop-type">${formatPropType(prop.prop_type)}</div>
        
        <div class="prop-line-section">
            <div class="prop-line-display">
                <span class="line-label">Line:</span>
                <span class="line-value">${displayLine}</span>
            </div>
        </div>
        
        <div class="odds-section">
            <div class="best-odds">
                <span style="font-size: 0.75rem; color: #64748b; margin-right: 0.5rem;">Best Odds</span>
                <span class="odds-value">${prop.odds || 'N/A'}</span>
                <span style="font-size: 0.75rem; color: #64748b; margin-left: 0.5rem;">FanDuel</span>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="btn-analyze" onclick="analyzeProp(${prop.prop_id})">
                Read full analysis
            </button>
          </div>
        `;
    
    // Add click handler
    card.addEventListener('click', () => {
        selectProp(card, prop);
    });
    
    return card;
}

function formatPropType(propType) {
    const typeMapping = {
        'To Record A Hit': 'Total Hits',
        'To Record A HR': 'Home Runs',
        'To Record An RBI': 'RBIs'
    };
    return typeMapping[propType] || propType;
}

function selectProp(cardElement, prop) {
    // Remove previous selection
    document.querySelectorAll('.prop-card').forEach(card => 
        card.classList.remove('selected'));
    
    // Add selection to clicked card
    cardElement.classList.add('selected');
    selectedPropId = prop.prop_id;
}

function analyzeProp(propId) {
    console.log('analyzeProp called with propId:', propId);
    console.log('Type of propId:', typeof propId);
    
    // Find the prop
    const prop = propsData.find(p => p.prop_id === propId);
    console.log('Found prop:', prop);
    console.log('propsData contains:', propsData.length, 'props');
    
    if (!prop) {
        console.error('Prop not found for ID:', propId);
        console.log('Available prop IDs:', propsData.map(p => p.prop_id));
        alert('Error: Prop not found. Please refresh the page and try again.');
        return;
    }

    // Show the modal immediately with prop info
    try {
    showAnalysisModal(prop);
    } catch (error) {
        console.error('Error showing modal:', error);
        alert('Error: Unable to open analysis modal. Please check the console for details.');
        return;
    }
    
    // loadMatchupData is now called from within showAnalysisModal after the modal is displayed
}

function showAnalysisModal(prop) {
    console.log('showAnalysisModal called with prop:', prop);
    
    const modal = document.getElementById('analysis-modal');
    if (!modal) {
        console.error('Modal element not found');
        return;
    }

    console.log('Modal found, checking for player cards...');
    
    // Debug: Check what elements exist in the modal
    const allElements = modal.querySelectorAll('*');
    console.log('Total elements in modal:', allElements.length);
    
    const analysisPlayerCards = modal.querySelectorAll('.analysis-player-card');
    console.log('Found .analysis-player-card elements:', analysisPlayerCards.length);
    
    // Try alternative selectors in case there's a CSS issue
    const divElements = modal.querySelectorAll('div');
    console.log('Total div elements in modal:', divElements.length);
    
    // Check if the modal is actually visible
    console.log('Modal display style:', modal.style.display);
    console.log('Modal computed display:', window.getComputedStyle(modal).display);

    // Set header info
    const headerProp = modal.querySelector('.analysis-prop-title');
    const lineBadge = modal.querySelector('.analysis-line-badge');
    const oddsBadge = modal.querySelector('.analysis-odds-badge');
    
    if (headerProp) {
        const propType = formatPropType(prop.prop_type);
        const line = prop.line || '0.5';
        headerProp.textContent = `${propType} - Over ${line}`;
    }
    if (lineBadge) lineBadge.textContent = prop.line || '0.5';
    if (oddsBadge) oddsBadge.textContent = prop.odds || 'N/A';

    // Try to find player cards with more debugging
    const playerCards = modal.querySelectorAll('.analysis-player-card');
    console.log('Player cards found:', playerCards.length);
    
    if (playerCards.length === 0) {
        console.error('No player cards found! Checking all classes in modal...');
        const allClassElements = modal.querySelectorAll('[class*="analysis"]');
        console.log('Elements with "analysis" in class name:', allClassElements.length);
        allClassElements.forEach((el, index) => {
            console.log(`Element ${index}:`, el.className, el.tagName);
        });
    }
    
    // Set batter info (first player card)
    const batterCard = playerCards[0];
    
    if (batterCard) {
        const batterHeadshot = batterCard.querySelector('.analysis-headshot');
        const batterName = batterCard.querySelector('.analysis-player-name');
        const batterMeta = batterCard.querySelector('.analysis-player-meta');
        const batterLogo = batterCard.querySelector('.analysis-team-logo');
        
        if (batterHeadshot) {
            const headshotUrl = prop.player_espn_id ? 
                `/static/headshots/${prop.player_espn_id}.png` : 
                '/static/headshots/placeholder.svg';
            batterHeadshot.src = headshotUrl;
            batterHeadshot.onerror = function() { 
                this.src = '/static/headshots/placeholder.svg'; 
            };
        }
        if (batterName) batterName.textContent = prop.player_name || 'Unknown Player';
        if (batterMeta) batterMeta.textContent = `${prop.position || 'N/A'} • ${prop.player_team_abbr || 'N/A'}`;
        if (batterLogo && prop.player_team_id) {
            batterLogo.src = `/static/team_logos/${prop.player_team_id}.svg`;
            batterLogo.onerror = function() { 
                this.src = '/static/team_logos/placeholder.svg'; 
            };
        }
    }

    // Reset pitcher info to loading state
    const pitcherCard = playerCards[1];
    if (pitcherCard) {
        const pitcherHeadshot = pitcherCard.querySelector('.analysis-headshot');
        const pitcherName = pitcherCard.querySelector('.analysis-player-name');
        const pitcherMeta = pitcherCard.querySelector('.analysis-player-meta');
        const pitcherLogo = pitcherCard.querySelector('.analysis-team-logo');
        
        if (pitcherHeadshot) pitcherHeadshot.src = '/static/headshots/placeholder.svg';
        if (pitcherName) pitcherName.textContent = 'Loading...';
        if (pitcherMeta) pitcherMeta.textContent = 'Loading...';
        if (pitcherLogo) pitcherLogo.src = '/static/team_logos/placeholder.svg';
    }

    // Reset stats to loading state
    const statSections = ['batter-season-stats', 'batter-career-stats', 'pitcher-season-stats', 'pitcher-career-stats'];
    statSections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (section) {
            section.innerHTML = '<div class="analysis-stat-item"><span class="analysis-stat-label">Loading...</span><span class="analysis-stat-value">-</span></div>';
        }
    });

    // Show the modal FIRST before setting up content
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    // Add a small delay to ensure DOM is updated, then load data
    setTimeout(() => {
        const playerCardsAfterShow = modal.querySelectorAll('.analysis-player-card');
        console.log('Player cards found after modal shown:', playerCardsAfterShow.length);
        
        // Load the matchup data after modal is fully shown
        loadMatchupData(prop.prop_id, prop);
    }, 100);
}

async function loadMatchupData(propId, prop) {
    try {
        console.log(`Loading matchup data for prop ID: ${propId}`);
        const response = await fetch(`/api/prop/${propId}/matchup`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Received matchup data:', data);
        updateModalWithMatchupData(data, prop);
        
    } catch (error) {
        console.error('Error loading matchup data:', error);
        
        // Update modal to show error state
        const modal = document.getElementById('analysis-modal');
        if (modal) {
            const playerCards = modal.querySelectorAll('.analysis-player-card');
            const pitcherCard = playerCards[1];
            
            if (pitcherCard) {
                const pitcherName = pitcherCard.querySelector('.analysis-player-name');
                const pitcherMeta = pitcherCard.querySelector('.analysis-player-meta');
                if (pitcherName) pitcherName.textContent = 'Unable to load';
                if (pitcherMeta) pitcherMeta.textContent = 'Data unavailable';
            }
            
            // Show error in stats sections
            const pitcherSeasonStats = document.getElementById('pitcher-season-stats');
            const pitcherCareerStats = document.getElementById('pitcher-career-stats');
            
            if (pitcherSeasonStats) {
                pitcherSeasonStats.innerHTML = '<div class="analysis-stat-item"><span class="analysis-stat-label">Unable to load</span><span class="analysis-stat-value">-</span></div>';
            }
            if (pitcherCareerStats) {
                pitcherCareerStats.innerHTML = '<div class="analysis-stat-item"><span class="analysis-stat-label">Unable to load</span><span class="analysis-stat-value">-</span></div>';
            }
        }
    }
}

function updateModalWithMatchupData(data, prop) {
    console.log('=== UPDATING MODAL WITH MATCHUP DATA ===');
    console.log('Data received:', data);
    console.log('Prop data:', prop);
    
    const modal = document.getElementById('analysis-modal');
    if (!modal) {
        console.error('Modal not found!');
        return;
    }
    
    const playerCards = modal.querySelectorAll('.analysis-player-card');
    console.log('Found player cards:', playerCards.length);
    
    // Update batter info (first card) with API data
    const batterCard = playerCards[0];
    if (batterCard && data.batter) {
        console.log('Updating batter card with:', data.batter);
        const batterHeadshot = batterCard.querySelector('.analysis-headshot');
        const batterName = batterCard.querySelector('.analysis-player-name');
        const batterMeta = batterCard.querySelector('.analysis-player-meta');
        const batterLogo = batterCard.querySelector('.analysis-team-logo');
        
        console.log('Batter elements found:', {
            headshot: !!batterHeadshot,
            name: !!batterName,
            meta: !!batterMeta,
            logo: !!batterLogo
        });
        
        if (batterHeadshot) {
            const headshotUrl = data.batter.headshot || '/static/headshots/placeholder.svg';
            console.log('Setting batter headshot to:', headshotUrl);
            batterHeadshot.src = headshotUrl;
            batterHeadshot.onerror = function() { 
                console.log('Batter headshot failed to load, using placeholder');
                this.src = '/static/headshots/placeholder.svg'; 
            };
        }
        if (batterName) {
            const name = data.batter.name || prop.player_name;
            console.log('Setting batter name to:', name);
            batterName.textContent = name;
        }
        if (batterMeta) {
            const teamAbbr = data.batter.team?.abbr || prop.player_team_abbr;
            const meta = `${prop.position || 'N/A'} • ${teamAbbr}`;
            console.log('Setting batter meta to:', meta);
            batterMeta.textContent = meta;
        }
        if (batterLogo && data.batter.team?.id) {
            const logoUrl = `/static/team_logos/${data.batter.team.id}.svg`;
            console.log('Setting batter logo to:', logoUrl);
            batterLogo.src = logoUrl;
            batterLogo.onerror = function() { 
                console.log('Batter logo failed to load, using placeholder');
                this.src = '/static/team_logos/placeholder.svg'; 
            };
        }
    }
    
    // Update pitcher info (second card)
    const pitcherCard = playerCards[1];
    if (pitcherCard) {
        console.log('Updating pitcher card');
        const pitcherHeadshot = pitcherCard.querySelector('.analysis-headshot');
        const pitcherName = pitcherCard.querySelector('.analysis-player-name');
        const pitcherMeta = pitcherCard.querySelector('.analysis-player-meta');
        const pitcherLogo = pitcherCard.querySelector('.analysis-team-logo');
        
        if (data.pitcher && data.pitcher.name && data.pitcher.name !== 'N/A') {
            console.log('Updating pitcher with data:', data.pitcher);
            
            if (pitcherHeadshot) {
                const headshotUrl = data.pitcher.headshot || '/static/headshots/placeholder.svg';
                console.log('Setting pitcher headshot to:', headshotUrl);
                pitcherHeadshot.src = headshotUrl;
                pitcherHeadshot.onerror = function() { 
                    console.log('Pitcher headshot failed to load, using placeholder');
                    this.src = '/static/headshots/placeholder.svg'; 
                };
            }
            if (pitcherName) {
                console.log('Setting pitcher name to:', data.pitcher.name);
                pitcherName.textContent = data.pitcher.name;
            }
            if (pitcherMeta) {
                const teamAbbr = data.pitcher.team?.abbr || 'TBD';
                const meta = `P • ${teamAbbr}`;
                console.log('Setting pitcher meta to:', meta);
                pitcherMeta.textContent = meta;
            }
            if (pitcherLogo && data.pitcher.team?.id) {
                const logoUrl = `/static/team_logos/${data.pitcher.team.id}.svg`;
                console.log('Setting pitcher logo to:', logoUrl);
                pitcherLogo.src = logoUrl;
                pitcherLogo.onerror = function() { 
                    console.log('Pitcher logo failed to load, using placeholder');
                    this.src = '/static/team_logos/placeholder.svg'; 
                };
            }
        } else {
            console.log('No pitcher data available');
            if (pitcherName) pitcherName.textContent = 'TBD';
            if (pitcherMeta) pitcherMeta.textContent = 'Pitcher not announced';
        }
    }

    console.log('Updating stats sections...');
    // Update batter stats
    console.log('Batter season stats:', data.batter?.season_stats);
    console.log('Batter career stats:', data.batter?.career_stats);
    updateStatsSection('batter-season-stats', data.batter?.season_stats, 'batter');
    updateStatsSection('batter-career-stats', data.batter?.career_stats, 'batter');
    
    // Update pitcher stats
    if (data.pitcher && data.pitcher.name && data.pitcher.name !== 'N/A') {
        console.log('Updating pitcher stats with data:', data.pitcher);
        console.log('Pitcher season stats:', data.pitcher.season_stats);
        console.log('Pitcher career stats:', data.pitcher.career_stats);
        updateStatsSection('pitcher-season-stats', data.pitcher.season_stats, 'pitcher');
        updateStatsSection('pitcher-career-stats', data.pitcher.career_stats, 'pitcher');
    } else {
        console.log('No pitcher data found:', data.pitcher);
        // Show "not available" for pitcher stats
        const pitcherSeasonStats = document.getElementById('pitcher-season-stats');
        const pitcherCareerStats = document.getElementById('pitcher-career-stats');
        
        if (pitcherSeasonStats) {
            pitcherSeasonStats.innerHTML = '<div class="analysis-stat-item"><span class="analysis-stat-label">Pitcher TBD</span><span class="analysis-stat-value">-</span></div>';
        }
        if (pitcherCareerStats) {
            pitcherCareerStats.innerHTML = '<div class="analysis-stat-item"><span class="analysis-stat-label">Pitcher TBD</span><span class="analysis-stat-value">-</span></div>';
        }
    }
    
    console.log('=== MODAL UPDATE COMPLETE ===');
}

function updateStatsSection(elementId, stats, playerType) {
    console.log(`Updating stats section: ${elementId}`, stats, playerType);
    const container = document.getElementById(elementId);
    
    if (!container) {
        console.error(`Container not found for ${elementId}`);
        return;
    }
    
    if (!stats || Object.keys(stats).length === 0) {
        console.log(`No stats available for ${elementId}`);
        container.innerHTML = '<div class="analysis-stat-item"><span class="analysis-stat-label">No data available</span><span class="analysis-stat-value">-</span></div>';
        return;
    }
    
    // Select the most relevant stats based on player type
    let relevantStats;
    if (playerType === 'batter') {
        relevantStats = getBatterStats(stats);
        } else {
        relevantStats = getPitcherStats(stats);
    }
    
    console.log(`Relevant stats for ${elementId}:`, relevantStats);
    
    container.innerHTML = '';
    relevantStats.forEach(stat => {
        const statItem = document.createElement('div');
        statItem.className = 'analysis-stat-item';
        statItem.innerHTML = `
            <span class="analysis-stat-label">${stat.label}</span>
            <span class="analysis-stat-value">${stat.value}</span>
        `;
        container.appendChild(statItem);
    });
}

function getBatterStats(stats) {
    const statMapping = [
        { key: 'avg', label: 'Batting Average' },
        { key: 'h', label: 'Hits' },
        { key: 'hr', label: 'Home Runs' },
        { key: 'rbi', label: 'RBIs' }
    ];
    return statMapping.map(stat => ({
        label: stat.label,
        value: formatStatValue(stats[stat.key], stat.key)
    }));
}

function getPitcherStats(stats) {
    const statMapping = [
        { key: 'era', label: 'ERA' },
        { key: 'whip', label: 'WHIP' },
        { key: 'k_9', label: 'K/9' },
        { key: 'avg', label: 'Opp. Avg' }
    ];
    return statMapping.map(stat => ({
        label: stat.label,
        value: formatStatValue(stats[stat.key], stat.key)
    }));
}

function formatStatValue(value, statType) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    
    const num = parseFloat(value);
    if (isNaN(num)) {
        return value.toString();
    }
    
    // Handle counting stats (hits, home runs, RBIs, wins, etc.)
    if (['h', 'hr', 'rbi', 'w', 'l', 'sv', 'g', 'gs'].includes(statType)) {
        return Math.round(num).toString();
    }
    
    // Handle percentage/ratio stats with 3 significant digits
    if (num < 1) {
        // For values less than 1 (like .290 batting average)
        if (num < 0.1) {
            return num.toFixed(3); // .050 format
        } else {
            return num.toFixed(3).substring(1); // Remove leading 0: .290
        }
    } else {
        // For values >= 1 (like 1.23 ERA, 4.50 ERA)
        if (num < 10) {
            return num.toFixed(2); // 1.23, 4.50
        } else if (num < 100) {
            return num.toFixed(1); // 12.3
        } else {
            return Math.round(num).toString(); // 123
        }
    }
}

function closeAnalysisModal() {
    const modal = document.getElementById('analysis-modal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // Restore background scrolling
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    const modal = document.getElementById('analysis-modal');
    if (event.target === modal) {
        closeAnalysisModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('analysis-modal');
        if (modal.style.display === 'flex') {
            closeAnalysisModal();
        }
    }
});

function initializeFilters() {
    // Initialize team filter
    const teams = [...new Set(propsData.map(prop => prop.player_team_abbr))].sort();
    const teamSelect = document.getElementById('team-filter');
    teamSelect.innerHTML = '<option value="">All Teams</option>';
    teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team;
        option.textContent = team;
        teamSelect.appendChild(option);
    });
    
    // Add filter event listeners
    teamSelect.addEventListener('change', applyFilters);
}

function applyFilters() {
    const teamFilter = document.getElementById('team-filter').value;
    
    let filteredProps = propsData;
    
    // Apply team filter
    if (teamFilter) {
        filteredProps = filteredProps.filter(prop => prop.player_team_abbr === teamFilter);
    }
    
    renderProps(filteredProps);
    updatePropsCount(filteredProps.length);
}

function updatePropsCount(count) {
    const countElement = document.getElementById('props-count');
    if (countElement) {
        countElement.textContent = count;
    }
}

function showLoading(show) {
    const container = document.getElementById('props-container');
    if (show) {
        container.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <h3>Loading Player Props</h3>
                <p>Fetching the latest odds from FanDuel...</p>
            </div>
        `;
    }
}

function showError(message) {
    const errorBox = document.getElementById('error-box');
    if (errorBox) {
        errorBox.innerHTML = `
            <div class="alert alert-danger" style="margin: 1rem; padding: 1rem; background: #fee2e2; border: 1px solid #fecaca; border-radius: 0.5rem; color: #dc2626;">
                ${message}
            </div>
        `;
        errorBox.style.display = 'block';
    }
}

function hideError() {
    const errorBox = document.getElementById('error-box');
    if (errorBox) {
        errorBox.style.display = 'none';
    }
}

// Add navigation functions (placeholder for now)
function switchSection(section) {
    // Remove active class from all tabs
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    
    // Add active class to clicked tab
    event.target.classList.add('active');
    
    // For now, only props section is functional
    if (section === 'props') {
        // Reload props data
        loadInitialData();
        return;
    }
    
    // Placeholder for other sections
    const container = document.getElementById('props-container');
    switch(section) {
        case 'games':
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Games & Weather</h3>
                    <p>Coming soon - upcoming games with weather conditions</p>
                </div>
            `;
            break;
        case 'standings':
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Current Standings</h3>
                    <p>Coming soon - real-time MLB standings</p>
                </div>
            `;
            break;
        case 'stats':
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Stat Leaders</h3>
                    <p>Coming soon - customizable stat leaderboards</p>
                </div>
            `;
            break;
    }
} 