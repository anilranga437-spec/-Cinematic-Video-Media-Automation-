const videoInput = document.getElementById('videos');
const fileList = document.getElementById('file-list');
if (videoInput && fileList) {
  videoInput.addEventListener('change', () => {
    const files = Array.from(videoInput.files || []);
    fileList.textContent = files.length
      ? files.map(file => file.name).join(' · ')
      : 'No files selected';
  });
}
function bindRange(id, outputId, transform = value => value) {
  const input = document.getElementById(id);
  const output = document.getElementById(outputId);
  if (!input || !output) return;
  const update = () => output.textContent = transform(input.value);
  input.addEventListener('input', update);
  update();
}
bindRange('fade_duration', 'fade-output', value => Number(value).toFixed(1));
bindRange('title_size', 'size-output');
bindRange('watermark_opacity', 'opacity-output', value => Math.round(Number(value) * 100));
