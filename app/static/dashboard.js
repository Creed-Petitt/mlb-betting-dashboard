let propsData = [];
let teamsData = [];
let selectedPropId = null;
let currentFilters = {
    team: '',
    propType: '',
    game: '',
    date: 'upcoming'
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
        // Use current date filter
        const dateFilter = currentFilters.date || 'upcoming';
        const response = await fetch(`/api/props?per_page=1000&date_filter=${dateFilter}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        console.log(`API returned ${data.results.length} props, total available: ${data.total}`);
        
        // Deduplicate props - keep only the most recent prop per player
        const propsMap = new Map();
        data.results.forEach(prop => {
            const key = `${prop.player_id}-${prop.prop_type}`;
            if (!propsMap.has(key) || new Date(prop.date) > new Date(propsMap.get(key).date)) {
                propsMap.set(key, prop);
            }
        });
        
        propsData = Array.from(propsMap.values());
        console.log(`After deduplication: ${propsData.length} unique props`);
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
    
    // Set appropriate lines for different prop types
    let displayLine;
    if (prop.prop_type === 'To Record A Hit' || prop.prop_type === 'To Record An RBI' || prop.prop_type === 'To Hit A Home Run') {
        displayLine = '0.5'; // Yes/No props
    } else if (prop.prop_type === 'To Record 2+ RBIs') {
        displayLine = '1.5'; // 2+ RBIs
    } else {
        displayLine = prop.line || 'N/A';
    }
    
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
        
        <div class="prop-type">${formatPropType(prop.prop_type)} • ${formatPropDate(prop.date)}</div>
        
        <div class="prop-line-section">
            <div class="prop-line-display">
                <span class="line-label">Line:</span>
                <span class="line-value">${displayLine}</span>
            </div>
        </div>
        
        <div class="odds-section">
            <div class="best-odds">
                <span style="font-size: 0.75rem; color: #64748b; margin-right: 0.5rem;">Best Odds</span>
                <span class="odds-value">${formatAmericanOdds(prop.odds) || 'N/A'}</span>
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
        'To Record An RBI': 'RBI (1+)',
        'To Record 2+ RBIs': 'RBI (2+)',
        'To Hit A Home Run': 'Home Runs'
    };
    return typeMapping[propType] || propType;
}

function formatAmericanOdds(odds) {
    if (!odds || odds === 'N/A') return 'N/A';
    
    const numericOdds = parseInt(odds);
    if (isNaN(numericOdds)) return odds;
    
    // If positive, add + sign, if negative, already has - sign
    return numericOdds > 0 ? `+${numericOdds}` : `${numericOdds}`;
}

function formatPropDate(dateStr) {
    if (!dateStr) return 'Unknown Date';
    
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const propDate = new Date(dateStr);
    
    // Format as YYYY-MM-DD for comparison
    const todayStr = today.toISOString().split('T')[0];
    const tomorrowStr = tomorrow.toISOString().split('T')[0];
    const propDateStr = propDate.toISOString().split('T')[0];
    
    if (propDateStr === todayStr) {
        return 'Today';
    } else if (propDateStr === tomorrowStr) {
        return 'Tomorrow';
    } else {
        // Format as MM/DD
        return `${propDate.getMonth() + 1}/${propDate.getDate()}`;
    }
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
    if (oddsBadge) oddsBadge.textContent = formatAmericanOdds(prop.odds) || 'N/A';

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
    
    // Add prop type filter listener
    const propTypeSelect = document.getElementById('prop-type-filter');
    if (propTypeSelect) {
        propTypeSelect.addEventListener('change', applyFilters);
    }
    
    // Add date filter listener
    const dateSelect = document.getElementById('date-filter');
    if (dateSelect) {
        dateSelect.addEventListener('change', async function() {
            currentFilters.date = this.value;
            showLoading(true);
            try {
                await loadProps();
                applyFilters();
            } catch (error) {
                console.error('Error reloading props:', error);
                showError('Failed to reload props for selected date.');
            } finally {
                showLoading(false);
            }
        });
    }
}

function applyFilters() {
    const teamFilter = document.getElementById('team-filter').value;
    const propTypeFilter = document.getElementById('prop-type-filter').value;
    
    let filteredProps = propsData;
    
    // Apply team filter
    if (teamFilter) {
        filteredProps = filteredProps.filter(prop => prop.player_team_abbr === teamFilter);
    }
    
    // Apply prop type filter
    if (propTypeFilter) {
        filteredProps = filteredProps.filter(prop => prop.prop_type === propTypeFilter);
    }
    
    renderProps(filteredProps);
    updatePropsCount(filteredProps.length);
}

function updatePropsCount(count) {
    const countElement = document.getElementById('props-count');
    if (countElement) {
        countElement.textContent = count;
    }
    
    // Update filter info
    const filterInfo = document.getElementById('props-filter-info');
    if (filterInfo) {
        const dateFilter = currentFilters.date || 'upcoming';
        const filterLabels = {
            'upcoming': '(Today + Tomorrow)',
            'today': '(Today Only)',
            'tomorrow': '(Tomorrow Only)'
        };
        filterInfo.textContent = filterLabels[dateFilter] || '';
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

let standingsData = null;
let currentStandingsView = 'divisions';

function switchSection(section) {
    console.log('Switching to section:', section);
    
    // Hide all sections
    const sections = ['props-container', 'standings-container', 'games-container', 'stats-container'];
    sections.forEach(sectionId => {
        const element = document.getElementById(sectionId);
        if (element) element.style.display = 'none';
    });
    
    // Hide filters for non-props sections
    const filtersSection = document.querySelector('.filters-section');
    if (filtersSection) {
        filtersSection.style.display = section === 'props' ? 'block' : 'none';
    }
    
    // Hide props summary bar for non-props sections
    const propsSummaryBar = document.querySelector('.props-summary-bar');
    if (propsSummaryBar) {
        propsSummaryBar.style.display = section === 'props' ? 'flex' : 'none';
    }
    
    // Update nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    const activeTab = document.querySelector(`[onclick="switchSection('${section}')"]`);
    if (activeTab) activeTab.classList.add('active');
    
    // Show selected section
    const targetSection = document.getElementById(`${section}-container`);
    if (targetSection) {
        targetSection.style.display = 'block';
        
        // Load data for the section if needed
        if (section === 'standings' && !standingsData) {
            loadStandings();
        } else if (section === 'games') {
            loadGames();
        } else if (section === 'stats') {
            loadStatLeaders();
        }
    }
}

async function loadStandings() {
    try {
        const response = await fetch('/api/standings');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        standingsData = await response.json();
        renderStandings(currentStandingsView);
        
    } catch (error) {
        console.error('Error loading standings:', error);
        const standingsContent = document.getElementById('standings-content');
        if (standingsContent) {
            standingsContent.innerHTML = `
                <div class="error-state">
                    <h3>Error Loading Standings</h3>
                    <p>Unable to fetch current standings. Please try again later.</p>
                </div>
            `;
        }
    }
}

function showStandingsView(view) {
    currentStandingsView = view;
    
    // Update toggle buttons
    document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`[onclick="showStandingsView('${view}')"]`);
    if (activeBtn) activeBtn.classList.add('active');
    
    if (standingsData) {
        renderStandings(view);
    }
}

function renderStandings(view) {
    const container = document.getElementById('standings-content');
    if (!container || !standingsData) return;
    
    if (view === 'divisions') {
        renderDivisionStandings(container);
    } else {
        renderPlayoffPicture(container);
    }
}

function renderDivisionStandings(container) {
    const divisions = standingsData.divisions;
    
    let html = '<div class="standings-grid">';
    
    // Define the order of divisions for consistent layout
    const divisionOrder = ['AL East', 'AL Central', 'AL West', 'NL East', 'NL Central', 'NL West'];
    
    divisionOrder.forEach(divisionName => {
        if (divisions[divisionName]) {
            const teams = divisions[divisionName];
            html += `
                <div class="division-table">
                    <div class="division-header">${divisionName}</div>
                    <table class="standings-table">
                        <thead>
                            <tr>
                                <th>Team</th>
                                <th>W-L</th>
                                <th>PCT</th>
                                <th>GB</th>
                                <th>Streak</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            teams.forEach((team, index) => {
                const rowClass = index === 0 ? 'division-leader' : '';
                const streakClass = team.streak.startsWith('W') ? 'streak-win' : 'streak-loss';
                
                html += `
                    <tr class="${rowClass}">
                        <td>
                            <div class="team-cell">
                                <img class="standings-team-logo" 
                                     src="/static/team_logos/${team.team_id}.svg" 
                                     alt="${team.abbr}"
                                     onerror="this.style.display='none'">
                                <div class="team-info">
                                    <div class="team-abbr-large">${team.abbr}</div>
                                </div>
                            </div>
                        </td>
                        <td class="record-cell">${team.wins}-${team.losses}</td>
                        <td class="pct-cell">${team.pct.toFixed(3)}</td>
                        <td class="gb-cell">${team.gb === 0 ? '-' : team.gb}</td>
                        <td class="streak-cell ${streakClass}">${team.streak}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function renderPlayoffPicture(container) {
    const playoffs = standingsData.playoffs;
    
    let html = '<div class="playoff-grid">';
    
    ['AL', 'NL'].forEach(league => {
        const leagueData = playoffs[league];
        const leagueName = league === 'AL' ? 'American League' : 'National League';
        
        html += `
            <div class="playoff-section">
                <div class="playoff-section-header">${leagueName}</div>
                
                <!-- Division Leaders -->
                <div class="playoff-category">
                    <div class="playoff-category-header clinched">Division Leaders</div>
        `;
        
        if (leagueData.division_leaders && leagueData.division_leaders.length > 0) {
            leagueData.division_leaders.forEach(team => {
                html += `
                    <div class="compact-team-row">
                        <div class="compact-team-info">
                            <img class="compact-team-logo" 
                                 src="/static/team_logos/${team.team_id}.svg" 
                                 alt="${team.abbr}"
                                 onerror="this.style.display='none'">
                            <span class="compact-team-name">${team.abbr}</span>
                        </div>
                        <div class="compact-team-stats">
                            <span class="compact-record">${team.wins}-${team.losses}</span>
                            <span class="compact-pct">${team.pct.toFixed(3)}</span>
                        </div>
                    </div>
                `;
            });
        } else {
            html += '<div class="compact-team-row"><span class="compact-team-name">No data available</span></div>';
        }
        
        html += `
                </div>
                
                <!-- Wild Card Teams -->
                <div class="playoff-category">
                    <div class="playoff-category-header wildcard">Wild Card</div>
        `;
        
        if (leagueData.wild_cards && leagueData.wild_cards.length > 0) {
            leagueData.wild_cards.forEach(team => {
                html += `
                    <div class="compact-team-row">
                        <div class="compact-team-info">
                            <img class="compact-team-logo" 
                                 src="/static/team_logos/${team.team_id}.svg" 
                                 alt="${team.abbr}"
                                 onerror="this.style.display='none'">
                            <span class="compact-team-name">${team.abbr}</span>
                        </div>
                        <div class="compact-team-stats">
                            <span class="compact-record">${team.wins}-${team.losses}</span>
                            <span class="compact-pct">${team.pct.toFixed(3)}</span>
                        </div>
                    </div>
                `;
            });
        } else {
            html += '<div class="compact-team-row"><span class="compact-team-name">No wild card teams</span></div>';
        }
        
        html += `
                </div>
                
                <!-- In the Hunt -->
                <div class="playoff-category">
                    <div class="playoff-category-header in-hunt">In the Hunt</div>
        `;
        
        if (leagueData.in_hunt && leagueData.in_hunt.length > 0) {
            leagueData.in_hunt.forEach(team => {
                html += `
                    <div class="compact-team-row">
                        <div class="compact-team-info">
                            <img class="compact-team-logo" 
                                 src="/static/team_logos/${team.team_id}.svg" 
                                 alt="${team.abbr}"
                                 onerror="this.style.display='none'">
                            <span class="compact-team-name">${team.abbr}</span>
                        </div>
                        <div class="compact-team-stats">
                            <span class="compact-record">${team.wins}-${team.losses}</span>
                            <span class="compact-pct">${team.pct.toFixed(3)}</span>
                        </div>
                    </div>
                `;
            });
        } else {
            html += '<div class="compact-team-row"><span class="compact-team-name">No teams in hunt</span></div>';
        }
        
        html += `
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Load game odds
async function loadGames() {
    try {
        showGamesLoading(true);
        
        const response = await fetch('/api/game-odds?date_filter=upcoming');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        renderGames(data.games);
        updateGamesCount(data.total);
        
    } catch (error) {
        console.error('Error loading games:', error);
        showGamesError('Unable to fetch game odds. Please try again later.');
    } finally {
        showGamesLoading(false);
    }
}

function renderGames(games) {
    const container = document.getElementById('games-content');
    if (!container) return;
    
    if (!games || games.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No Games Available</h3>
                <p>No upcoming games with odds found.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    games.forEach(game => {
        html += createGameCard(game);
    });
    
    container.innerHTML = html;
}

function createGameCard(game) {
    // Convert from Eastern to Central time (subtract 1 hour)
    const gameTimeEST = new Date(game.commence_time);
    const gameTimeCST = new Date(gameTimeEST.getTime() - (1 * 60 * 60 * 1000));
    
    const gameTime = gameTimeCST.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short', 
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
        timeZone: 'America/Chicago'
    });
    
    // Build bookmaker odds
    let oddsHtml = '';
    const bookmakerOrder = ['fanduel', 'draftkings', 'betmgm'];
    
    bookmakerOrder.forEach(bookmaker => {
        if (game.bookmakers[bookmaker]) {
            const odds = game.bookmakers[bookmaker];
            oddsHtml += `
                <div class="bookmaker-odds">
                    <div class="bookmaker-name">${formatBookmakerName(bookmaker)}</div>
                    <div class="odds-row">
                        <div class="team-odds">
                            <span class="team-name-small">${game.away_team}</span>
                            <span class="odds-value ${odds.away_odds > 0 ? 'positive' : 'negative'}">
                                ${formatOdds(odds.away_odds)}
                            </span>
                        </div>
                    </div>
                    <div class="odds-row">
                        <div class="team-odds">
                            <span class="team-name-small">${game.home_team}</span>
                            <span class="odds-value ${odds.home_odds > 0 ? 'positive' : 'negative'}">
                                ${formatOdds(odds.home_odds)}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    return `
        <div class="game-card">
            <div class="game-header">
                <div class="game-matchup">
                    <span class="team-name">${game.away_team}</span>
                    <span class="game-vs">@</span>
                    <span class="team-name">${game.home_team}</span>
                </div>
                <div class="game-time">${gameTime}</div>
            </div>
            <div class="odds-grid">
                ${oddsHtml}
            </div>
        </div>
    `;
}

function formatBookmakerName(bookmaker) {
    const names = {
        'fanduel': 'FanDuel',
        'draftkings': 'DraftKings', 
        'betmgm': 'BetMGM'
    };
    return names[bookmaker] || bookmaker;
}

function formatOdds(odds) {
    return odds > 0 ? `+${odds}` : `${odds}`;
}

function updateGamesCount(count) {
    const countElement = document.getElementById('games-count');
    if (countElement) {
        countElement.textContent = count;
    }
}

function showGamesLoading(show) {
    const container = document.getElementById('games-content');
    if (!container) return;
    
    if (show) {
        container.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <h3>Loading Game Odds</h3>
                <p>Fetching odds from multiple sportsbooks...</p>
            </div>
        `;
    }
}

function showGamesError(message) {
    const container = document.getElementById('games-content');
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <h3>Error Loading Games</h3>
                <p>${message}</p>
            </div>
        `;
    }
}

// Stat Leaders functionality
let statLeadersData = { individual: [], team: [], categories: [] };

function loadStatLeaders() {
    console.log('Loading stat leaders...');
    
    // Load categories first
    fetch('/api/stat-leaders/categories')
        .then(response => response.json())
        .then(data => {
            statLeadersData.categories = data;
            setupStatLeadersInterface();
            
            // Load default data (individual stats)
            loadIndividualLeaders('homeRuns');
        })
        .catch(error => {
            console.error('Error loading stat leader categories:', error);
            showStatLeadersError('Failed to load categories');
        });
}

function setupStatLeadersInterface() {
    const container = document.getElementById('stat-leaders-content');
    
    const html = `
        <div class="stat-leaders-header">
            <h2>📊 Stat Leaders</h2>
            <div class="stat-leaders-summary">Current season leaders - Batters, Pitchers, and Teams</div>
        </div>
        
        <div class="stat-leaders-controls">
            <div class="stat-leaders-toggle">
                <button id="batters-toggle" class="toggle-btn active" onclick="switchStatType('batters')">
                    🏏 Batters
                </button>
                <button id="pitchers-toggle" class="toggle-btn" onclick="switchStatType('pitchers')">
                    ⚾ Pitchers
                </button>
                <button id="teams-toggle" class="toggle-btn" onclick="switchStatType('teams')">
                    🏟️ Teams
                </button>
            </div>
            
            <div class="stat-controls">
                <select id="category-select" class="category-select">
                    ${statLeadersData.categories.batting?.map(cat => 
                        `<option value="${cat.category}">${cat.display_name}</option>`
                    ).join('') || ''}
                </select>
                <select id="limit-select" class="limit-select">
                    <option value="10">Top 10</option>
                    <option value="25" selected>Top 25</option>
                    <option value="50">Top 50</option>
                </select>
            </div>
        </div>

        <div id="stat-leaders-results" class="stat-leaders-results">
            <div class="loading">Loading stat leaders...</div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Add event listeners
    document.getElementById('category-select').addEventListener('change', (e) => {
        const limit = document.getElementById('limit-select').value;
        const currentType = getCurrentStatType();
        
        loadCurrentStatType(currentType, e.target.value, parseInt(limit));
    });
    
    document.getElementById('limit-select').addEventListener('change', (e) => {
        const category = document.getElementById('category-select').value;
        const currentType = getCurrentStatType();
        
        loadCurrentStatType(currentType, category, parseInt(e.target.value));
    });
}

function getCurrentStatType() {
    const activeToggle = document.querySelector('.toggle-btn.active');
    if (activeToggle.id === 'batters-toggle') return 'batters';
    if (activeToggle.id === 'pitchers-toggle') return 'pitchers';
    if (activeToggle.id === 'teams-toggle') return 'teams';
    return 'batters';
}

function loadCurrentStatType(type, category, limit) {
    if (type === 'batters' || type === 'pitchers') {
        loadIndividualLeaders(category, limit);
    } else if (type === 'teams') {
        loadTeamLeaders(category, limit);
    }
}

// Make switchStatType available globally
window.switchStatType = function(type) {
    console.log(`[DEBUG] Switching to ${type} stat type`);
    
    // Update toggle buttons
    document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${type}-toggle`).classList.add('active');
    
    // Update category dropdown
    const categorySelect = document.getElementById('category-select');
    let categories;
    
    if (type === 'batters') {
        categories = statLeadersData.categories.batting;
    } else if (type === 'pitchers') {
        categories = statLeadersData.categories.pitching;
    } else if (type === 'teams') {
        categories = statLeadersData.categories.team;
    }
    
    console.log(`[DEBUG] Categories for ${type}:`, categories);
    
    categorySelect.innerHTML = categories?.map(cat => 
        `<option value=\"${cat.category}\">${cat.display_name}</option>`
    ).join('') || '';
    
    // Update limit options based on type
    const limitSelect = document.getElementById('limit-select');
    if (type === 'teams') {
        limitSelect.innerHTML = `
            <option value=\"10\" selected>Top 10</option>
            <option value=\"15\">Top 15</option>
            <option value=\"30\">All Teams</option>
        `;
    } else {
        limitSelect.innerHTML = `
            <option value=\"10\">Top 10</option>
            <option value=\"25\" selected>Top 25</option>
            <option value=\"50\">Top 50</option>
        `;
    }
    
    // Load data for the selected type
    const category = categorySelect.value;
    const limit = parseInt(limitSelect.value);
    
    console.log(`[DEBUG] Loading ${type} data: category=${category}, limit=${limit}`);
    
    loadCurrentStatType(type, category, limit);
};

function loadIndividualLeaders(category = 'homeRuns', limit = 25) {
    const container = document.getElementById('stat-leaders-results');
    container.innerHTML = '<div class="loading">Loading individual leaders...</div>';
    
    console.log(`[DEBUG] Loading individual leaders: category=${category}, limit=${limit}`);
    
    fetch(`/api/stat-leaders/individual?category=${category}&limit=${limit}`)
        .then(response => {
            console.log(`[DEBUG] Response status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(`[DEBUG] Received data:`, data);
            console.log(`[DEBUG] Results count: ${data.results?.length || 0}`);
            
            statLeadersData.individual = data.results;
            renderIndividualLeaders(data.results, category);
        })
        .catch(error => {
            console.error('Error loading individual leaders:', error);
            container.innerHTML = '<div class="error">Failed to load individual leaders</div>';
        });
}

function loadTeamLeaders(category = 'teamBattingAverage', limit = 10) {
    const container = document.getElementById('stat-leaders-results');
    container.innerHTML = '<div class="loading">Loading team leaders...</div>';
    
    fetch(`/api/stat-leaders/teams?category=${category}&limit=${limit}`)
        .then(response => response.json())
        .then(data => {
            statLeadersData.team = data.results;
            renderTeamLeaders(data.results, category);
        })
        .catch(error => {
            console.error('Error loading team leaders:', error);
            container.innerHTML = '<div class="error">Failed to load team leaders</div>';
        });
}

function renderIndividualLeaders(leaders, category) {
    const container = document.getElementById('stat-leaders-results');
    
    if (!leaders || leaders.length === 0) {
        container.innerHTML = '<div class="no-data">No individual leaders found</div>';
        return;
    }
    
    let html = '<div class="leaders-grid individual-leaders-grid">';
    
    leaders.forEach((leader, index) => {
        const valueFormatted = formatStatLeaderValue(leader.value, category);
        
        html += `
            <div class="leader-card">
                <div class="leader-rank">#${leader.rank}</div>
                <div class="leader-player-info">
                    <img class="leader-headshot" 
                         src="${leader.headshot || '/static/headshots/placeholder.png'}" 
                         alt="${leader.player_name}"
                         onerror="this.src='/static/headshots/placeholder.png'">
                    <div class="leader-player-details">
                        <div class="leader-player-name">${leader.player_name}</div>
                        <div class="leader-team-info">
                            <img class="leader-team-logo" 
                                 src="${leader.team_logo || ''}" 
                                 alt="${leader.team_name || ''}"
                                 onerror="this.style.display='none'">
                            <span class="leader-team-name">${leader.team_name || 'Free Agent'}</span>
                        </div>
                    </div>
                </div>
                <div class="leader-stat-value">${valueFormatted}</div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function renderTeamLeaders(leaders, category) {
    const container = document.getElementById('stat-leaders-results');
    
    if (!leaders || leaders.length === 0) {
        container.innerHTML = '<div class="no-data">No team leaders found</div>';
        return;
    }
    
    let html = '<div class="leaders-grid team-leaders-grid">';
    
    leaders.forEach((leader, index) => {
        const valueFormatted = formatStatLeaderValue(leader.value, category);
        
        html += `
            <div class="leader-card team-leader-card">
                <div class="leader-rank">#${leader.rank}</div>
                <div class="leader-team-info-full">
                    <img class="leader-team-logo-large" 
                         src="${leader.team_logo}" 
                         alt="${leader.team_name}"
                         onerror="this.style.display='none'">
                    <div class="leader-team-name">${leader.team_name}</div>
                </div>
                <div class="leader-stat-value">${valueFormatted}</div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function formatStatLeaderValue(value, category) {
    if (!value || value === '') return '-';
    
    const num = parseFloat(value);
    if (isNaN(num)) return value;
    
    // Handle percentage stats that should show full decimal
    if (['battingAverage', 'teamBattingAverage', 'onBasePercentage', 'teamOnBasePercentage', 
         'sluggingPercentage', 'teamSluggingPercentage'].includes(category)) {
        if (num < 1) {
            return num.toFixed(3).substring(1); // Remove leading 0: .290
        }
        return num.toFixed(3);
    }
    
    // Handle ERA and WHIP
    if (['era', 'teamERA', 'whip', 'teamWHIP'].includes(category)) {
        return num.toFixed(2);
    }
    
    // Handle OPS
    if (['onBasePlusSlugging', 'teamOPS'].includes(category)) {
        return num.toFixed(3);
    }
    
    // Handle counting stats (whole numbers)
    if (['homeRuns', 'teamHomeRuns', 'rbi', 'teamRBI', 'hits', 'teamHits', 'runs', 'teamRuns',
         'wins', 'teamWins', 'strikeouts', 'teamStrikeouts', 'saves', 'teamSaves', 
         'stolenBases', 'doubles', 'triples'].includes(category)) {
        return Math.round(num).toString();
    }
    
    // Default formatting
    return num.toString();
}

function showStatLeadersError(message) {
    const container = document.getElementById('stat-leaders-content');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadInitialData();
}); 