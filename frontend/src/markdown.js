// 共享 Markdown 渲染器：markdown-it + highlight.js。
// 首页介绍（HomeView）与 Lab 指南（LabDetailView）共用，避免重复配置与高亮逻辑。
import MarkdownIt from 'markdown-it'
import hljs from './highlight'
import 'highlight.js/styles/github-dark.css'

export function createMarkdown(options = {}) {
  const md = new MarkdownIt({
    // 开放内联 HTML（如 <img> / <br> / 自定义 <div>），内容均为本地受信文件（intro.md / 后端 Lab guide），无 XSS 风险。
    html: true,
    linkify: true,
    breaks: false,
    ...options,
    highlight(str, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          const value = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
          return `<pre class="hljs"><code>${value}</code></pre>`
        } catch {
          /* 高亮失败走下方兜底 */
        }
      }
      return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
    },
  })
  return md
}
