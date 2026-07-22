// Live avatar preview on the edit-profile page. Origin-local + CSP-safe
// (no inline script). Shows the chosen image before the form is submitted.
(function () {
  'use strict';
  var input = document.getElementById('id_avatar');
  if (!input) {
    return;
  }
  input.addEventListener('change', function (event) {
    var file = event.target.files && event.target.files[0];
    if (!file) {
      return;
    }
    var reader = new FileReader();
    reader.onload = function (loadEvent) {
      var preview = document.getElementById('avatar-preview');
      var placeholder = document.getElementById('avatar-placeholder');
      if (preview) {
        preview.src = loadEvent.target.result;
        preview.classList.remove('is-hidden');
      }
      if (placeholder) {
        placeholder.classList.add('is-hidden');
      }
    };
    reader.readAsDataURL(file);
  });
})();
