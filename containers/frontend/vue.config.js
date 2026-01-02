const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    host: '0.0.0.0',
    port: 8080,
    allowedHosts: 'all'
  },
  // Show linting warnings in development but don't block compilation
  // Enforce linting errors in production builds
  lintOnSave: process.env.NODE_ENV === 'development' ? 'warning' : true
})

