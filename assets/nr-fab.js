(function () {
  var card = document.querySelector('.nr-fab-wrap');
  if (!card) return;
  try {
    if (sessionStorage.getItem('nrFabDismissed')) {
      card.style.display = 'none';
      return;
    }
  } catch (e) {}
  var closeBtn = card.querySelector('.nr-fab-close');
  if (!closeBtn) return;
  closeBtn.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    card.style.display = 'none';
    try { sessionStorage.setItem('nrFabDismissed', '1'); } catch (ex) {}
  });
})();
