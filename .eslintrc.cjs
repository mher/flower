module.exports = {
  env: { browser: true, es2020: true },
  ignorePatterns: ["**/datatables-1.13.4.min.js"],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': 'warn',
    'prefer-spread': 'off',
  },
};
