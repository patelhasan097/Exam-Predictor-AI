// ============================================
// EXAM PREDICTOR - JavaScript
// ============================================

// Hamburger Menu
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');

if (hamburger) {
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
  });
}

// Mode Toggle
const modeBtns = document.querySelectorAll('.mode-btn');
const uploadSection = document.getElementById('uploadSection');
let currentMode = 'demo';

modeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    modeBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentMode = btn.dataset.mode;

    if (currentMode === 'pdf') {
      uploadSection.style.display = 'block';
    } else {
      uploadSection.style.display = 'none';
    }
  });
});

// File Upload
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
let selectedFiles = [];

if (uploadArea) {
  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
  });
}

if (fileInput) {
  fileInput.addEventListener('change', () => {
    handleFiles(fileInput.files);
  });
}

function handleFiles(files) {
  selectedFiles = Array.from(files).filter(f => f.name.endsWith('.pdf'));
  fileList.innerHTML = '';

  selectedFiles.forEach(file => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
      <span>✅</span>
      <span>${file.name}</span>
      <span style="color: var(--text-muted); margin-left: auto;">
        ${(file.size / 1024 / 1024).toFixed(1)} MB
      </span>
    `;
    fileList.appendChild(item);
  });
}

// Analyze Button
const analyzeBtn = document.getElementById('analyzeBtn');

if (analyzeBtn) {
  analyzeBtn.addEventListener('click', async () => {
    const exam = document.getElementById('examSelect').value;
    showLoading();

    try {
      const formData = new FormData();
      formData.append('exam', exam);
      formData.append('mode', currentMode);

      if (currentMode === 'pdf' && selectedFiles.length > 0) {
        selectedFiles.forEach(file => {
          formData.append('pdfs', file);
        });
      }

      const response = await fetch('/analyze', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      hideLoading();

      if (data.success) {
        showResults(data);
      } else {
        alert('Error: ' + data.error);
      }

    } catch (error) {
      hideLoading();
      alert('Kuch problem ho gayi. Try karo dobara.');
    }
  });
}

// Loading
function showLoading() {
  document.getElementById('loadingOverlay').classList.add('show');
  animateLoadingSteps();
}

function hideLoading() {
  document.getElementById('loadingOverlay').classList.remove('show');
}

function animateLoadingSteps() {
  const steps = document.querySelectorAll('.loading-step');
  let i = 0;
  const interval = setInterval(() => {
    steps.forEach(s => s.classList.remove('active'));
    if (i < steps.length) {
      steps[i].classList.add('active');
      i++;
    } else {
      clearInterval(interval);
    }
  }, 800);
}

// Show Results
function showResults(data) {
  const resultsSection = document.getElementById('results');
  resultsSection.style.display = 'block';

  // Scroll to results
  setTimeout(() => {
    resultsSection.scrollIntoView({ behavior: 'smooth' });
  }, 100);

  // Update header
  document.getElementById('resultsExam').textContent = data.exam;
  document.getElementById('resultsMode').textContent =
    data.mode === 'demo' ? '📊 Demo Mode' : `📄 ${data.files_processed} PDFs`;

  const predictions = data.predictions;

  // Stats
  const high = predictions.filter(p => p.priority === 'high').length;
  const medium = predictions.filter(p => p.priority === 'medium').length;
  const low = predictions.filter(p => p.priority === 'low').length;

  document.getElementById('statTotal').textContent = predictions.length;
  document.getElementById('statHigh').textContent = high;
  document.getElementById('statMedium').textContent = medium;
  document.getElementById('statLow').textContent = low;

  // Heatmap
  renderHeatmap(predictions);

  // Progress bars
  renderProgress(predictions);

  // Study plan
  renderStudyPlan(predictions, data.exam);

  // Activate first tab
  switchTab('heatmap');
}

// Heatmap
function renderHeatmap(predictions) {
  const highCol = document.getElementById('highTopics');
  const medCol = document.getElementById('mediumTopics');
  const lowCol = document.getElementById('lowTopics');

  highCol.innerHTML = '';
  medCol.innerHTML = '';
  lowCol.innerHTML = '';

  predictions.forEach(p => {
    const card = `
      <div class="topic-card ${p.priority}">
        <div class="topic-name">${p.topic}</div>
        <div class="topic-prob">${p.probability}% Probability</div>
        <div class="topic-reason">${p.reason}</div>
      </div>
    `;

    if (p.priority === 'high') highCol.innerHTML += card;
    else if (p.priority === 'medium') medCol.innerHTML += card;
    else lowCol.innerHTML += card;
  });
}

// Progress Bars
function renderProgress(predictions) {
  const container = document.getElementById('progressList');
  container.innerHTML = '';

  const sorted = [...predictions].sort((a, b) => b.probability - a.probability);

  sorted.forEach(p => {
    const item = document.createElement('div');
    item.className = 'progress-item';
    item.innerHTML = `
      <div class="progress-header">
        <span class="progress-name">${p.topic}</span>
        <span class="progress-pct">${p.probability}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" data-width="${p.probability}"></div>
      </div>
    `;
    container.appendChild(item);
  });

  // Animate bars
  setTimeout(() => {
    document.querySelectorAll('.progress-fill').forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  }, 100);
}

// Study Plan
function renderStudyPlan(predictions, exam) {
  const high = predictions.filter(p => p.priority === 'high');
  const total = predictions.length;

  document.getElementById('planMustStudy').textContent = high.length;
  document.getElementById('planTotal').textContent = total;
  document.getElementById('planTimeSave').textContent =
    `${(total - high.length) * 8}+ hrs`;

  // Top 3
  const top3Container = document.getElementById('top3Topics');
  top3Container.innerHTML = '';

  const top3 = [...predictions]
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 3);

  top3.forEach((p, i) => {
    top3Container.innerHTML += `
      <div class="top-topic-item">
        <div class="rank-badge">#${i + 1}</div>
        <div class="top-topic-info">
          <h4>${p.topic}</h4>
          <p>${p.probability}% chance • ${p.reason}</p>
        </div>
      </div>
    `;
  });
}

// Tabs
function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.toggle('active', content.id === tabName + 'Tab');
  });

  if (tabName === 'analysis') {
    setTimeout(() => {
      document.querySelectorAll('.progress-fill').forEach(bar => {
        bar.style.width = bar.dataset.width + '%';
      });
    }, 100);
  }
}

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth' });
      navLinks.classList.remove('open');
    }
  });
});