// ────────────────────────────────────────────────────────────
// 时空呼吸 v3 Aurora · 粒子背景 + 鼠标光晕
// ────────────────────────────────────────────────────────────
(function () {
  if (window.__particleInit) return;
  window.__particleInit = true;

  // 鼠标位置 -> CSS 变量(驱动 .stApp::after 光晕)
  document.addEventListener('mousemove', function (e) {
    var x = (e.clientX / window.innerWidth) * 100;
    var y = (e.clientY / window.innerHeight) * 100;
    document.documentElement.style.setProperty('--mx', x + '%');
    document.documentElement.style.setProperty('--my', y + '%');
  });

  // 粒子系统
  var c = document.getElementById('particle-bg');
  if (!c) return;
  var ctx = c.getContext('2d');
  var W, H;
  var particles = [];
  var N = window.innerWidth < 768 ? 35 : 80;

  function resize() {
    W = c.width = window.innerWidth;
    H = c.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  function getColor() {
    var meta = window.__bhiMeta || { color: '#00d4ff' };
    return meta.color;
  }

  function spawn() {
    return {
      x: Math.random() * W,
      y: H + Math.random() * 40,
      r: Math.random() * 1.6 + 0.4,
      vy: -(Math.random() * 0.35 + 0.12),
      vx: (Math.random() - 0.5) * 0.12,
      o: Math.random() * 0.5 + 0.15,
      ph: Math.random() * Math.PI * 2,
      life: 0,
      maxLife: 600 + Math.random() * 400
    };
  }

  for (var i = 0; i < N; i++) {
    particles.push(spawn());
    particles[i].y = Math.random() * H;
    particles[i].life = Math.random() * particles[i].maxLife;
  }

  function tick() {
    ctx.clearRect(0, 0, W, H);
    var color = getColor();
    var r = 0, g = 212, b = 255;
    if (color && color[0] === '#' && color.length === 7) {
      r = parseInt(color.slice(1, 3), 16);
      g = parseInt(color.slice(3, 5), 16);
      b = parseInt(color.slice(5, 7), 16);
    }

    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.life++;
      p.x += p.vx + Math.sin(p.life * 0.008 + p.ph) * 0.25;
      p.y += p.vy;
      var fade = Math.min(1, Math.min(p.life, p.maxLife - p.life) / 80);
      var a = p.o * fade;

      ctx.beginPath();
      ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();

      var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 6);
      grad.addColorStop(0, 'rgba(' + r + ',' + g + ',' + b + ',' + (a * 0.35) + ')');
      grad.addColorStop(1, 'rgba(' + r + ',' + g + ',' + b + ',0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 6, 0, Math.PI * 2);
      ctx.fill();

      if (p.y < -10 || p.life > p.maxLife) {
        particles[i] = spawn();
      }
    }

    requestAnimationFrame(tick);
  }
  tick();
})();
