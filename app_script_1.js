
(function(){
  function showStudioPopup(){
    const o = document.getElementById('studio-popup-overlay');
    o.style.display = 'flex';
    requestAnimationFrame(() => o.classList.add('visible'));
  }
  window.closeStudioPopup = function(){
    const o = document.getElementById('studio-popup-overlay');
    o.classList.remove('visible');
    setTimeout(() => o.style.display = 'none', 300);
    if (IS_DEMO) setTimeout(showStudioPopup, 60000);
    // In real studio: mark as seen, never show again
    else { try { localStorage.setItem('imsg_promo_seen', '1'); } catch(e){} }
  };
  document.getElementById('studio-popup-overlay').addEventListener('click', function(e){
    if(e.target === this) window.closeStudioPopup();
  });
  if (IS_DEMO) {
    setTimeout(showStudioPopup, 10000);
  } else {
    // Real studio: show once after 5 minutes, only if never seen before
    try { if (localStorage.getItem('imsg_promo_seen')) return; } catch(e){}
    setTimeout(showStudioPopup, 300000);
  }
})();
