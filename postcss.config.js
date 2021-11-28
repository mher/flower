const purgecss = require('@fullhuman/postcss-purgecss')

module.exports = {
  plugins: [
    purgecss({
      content: ['./flower/templates/**/*.html', './flower/static/src/js/**/*.js'],
      safelist: {
        standard: [/^col-/]
      }
    })
  ]
}
