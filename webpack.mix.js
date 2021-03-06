let mix = require('laravel-mix');

mix.styles([
    'static-src/css/normalize.css',
    'static-src/css/highlight.css',
    'static-src/css/fontello.css',
    'static-src/css/styles.css'
], 'static/bundle.css');

mix.copyDirectory('static-src/font', 'static/font');
mix.copyDirectory('static-src/img', 'static/img');
