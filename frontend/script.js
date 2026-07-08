document.getElementById('prediction-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const teamA = document.getElementById('team-a').options[document.getElementById('team-a').selectedIndex].text;
    const teamB = document.getElementById('team-b').options[document.getElementById('team-b').selectedIndex].text;
    const venue = document.getElementById('venue').value;
    const btn = document.getElementById('predict-btn');
    
    // UI Loading State
    btn.innerHTML = '<span>Processing...</span>';
    btn.style.opacity = '0.7';
    document.getElementById('result-container').classList.add('hidden');

    try {
        // Prepare request body mapping what backend expects
        const requestBody = {
            match_id: `live_${Date.now()}`,
            sport: "cricket",
            match_type: "t20",
            date: new Date().toISOString().split('T')[0],
            venue: venue,
            team_a: teamA,
            team_b: teamB,
            toss: teamA
        };

        // Call the Railway API (Update URL once deployed!)
        // e.g. https://globalpulse-production.up.railway.app/predict
        const apiUrl = 'http://localhost:8000/predict'; 

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        
        // Update UI with results
        showResults(data.winner, data.probability, data.confidence);

    } catch (error) {
        console.error('Error fetching prediction:', error);
        alert('Failed to connect to the prediction engine. Make sure the backend is running!');
    } finally {
        // Reset Button
        btn.innerHTML = '<span>Generate Prediction</span>';
        btn.style.opacity = '1';
    }
});

function showResults(winner, probability, confidence) {
    const resultContainer = document.getElementById('result-container');
    const winnerEl = document.getElementById('predicted-winner');
    const probBar = document.getElementById('prob-bar');
    const probVal = document.getElementById('prob-val');
    const confBar = document.getElementById('conf-bar');
    const confVal = document.getElementById('conf-val');

    // Convert decimal to percentage
    const probPct = Math.round(probability * 100);
    const confPct = Math.round(confidence * 100);

    winnerEl.textContent = winner;
    
    // Reset bars for animation
    probBar.style.width = '0%';
    confBar.style.width = '0%';
    
    // Reveal container
    resultContainer.classList.remove('hidden');

    // Trigger animations slightly after reveal
    setTimeout(() => {
        probBar.style.width = `${probPct}%`;
        probVal.textContent = `${probPct}%`;
        
        confBar.style.width = `${confPct}%`;
        confVal.textContent = `${confPct}%`;
    }, 100);
}
