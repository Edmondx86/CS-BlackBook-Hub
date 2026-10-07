/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 品牌青绿（主色 / 强调）—— 值定义在 src/theme.css
        brand: {
          DEFAULT: 'rgb(var(--brand) / <alpha-value>)',
          light: 'rgb(var(--brand-light) / <alpha-value>)',
          dark: 'rgb(var(--brand-dark) / <alpha-value>)',
        },
        // 主题紫（次色 / 强调）—— 值定义在 src/theme.css
        theme: {
          DEFAULT: 'rgb(var(--theme) / <alpha-value>)',
          light: 'rgb(var(--theme-light) / <alpha-value>)',
          dark: 'rgb(var(--theme-dark) / <alpha-value>)',
        },
        // 背景层级
        page: 'rgb(var(--bg-page) / <alpha-value>)',
        header: 'rgb(var(--bg-header) / <alpha-value>)',
        card: 'rgb(var(--bg-card) / <alpha-value>)',
        elevated: 'rgb(var(--bg-elevated) / <alpha-value>)',
        // 文字层级
        primary: 'rgb(var(--text-primary) / <alpha-value>)',
        secondary: 'rgb(var(--text-secondary) / <alpha-value>)',
        tertiary: 'rgb(var(--text-tertiary) / <alpha-value>)',
        muted: 'rgb(var(--text-muted) / <alpha-value>)',
        faint: 'rgb(var(--text-faint) / <alpha-value>)',
        inverse: 'rgb(var(--text-inverse) / <alpha-value>)',
        // 状态色
        danger: 'rgb(var(--danger) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        // 边框
        line: 'rgb(var(--border) / <alpha-value>)',
        'line-strong': 'rgb(var(--border-strong) / <alpha-value>)',
        // 卡片 / 按钮
        cardline: 'rgb(var(--card-border) / <alpha-value>)',
        btn: 'rgb(var(--btn-bg) / <alpha-value>)',
        'btn-hover': 'rgb(var(--btn-bg-hover) / <alpha-value>)',
        'btn-text': 'rgb(var(--btn-text) / <alpha-value>)',
        'btn-alt': 'rgb(var(--btn-bg-alt) / <alpha-value>)',
        'btn-alt-hover': 'rgb(var(--btn-bg-alt-hover) / <alpha-value>)',
        'btn-alt-text': 'rgb(var(--btn-text-alt) / <alpha-value>)',
      },
    },
  },
  plugins: [],
}
