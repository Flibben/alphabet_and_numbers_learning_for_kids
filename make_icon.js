const sharp = require('sharp');

// Take the SVG, resize to exactly 512x512, and save as PNG
sharp('assets/icon.svg')
  .resize(512, 512)
  .png()
  .toFile('play_store_icon.png')
  .then(() => console.log('✅ Success! Your 512x512 PNG is ready.'))
  .catch(err => console.error('Oops, an error occurred:', err));