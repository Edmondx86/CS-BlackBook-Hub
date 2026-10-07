// highlight.js 按需注册。
//
// 直接 `import hljs from 'highlight.js'` 会把 node_modules/highlight.js/lib/languages
// 下 386 个文件（约 1.58 MB，覆盖 ~190 种语言）全部打进 bundle，而本站内容实际只用到
// python / bash / text 三种代码围栏。因此改为 core + 按需注册，体积可降到几十 KB。
//
// 注意：未注册的语言不会报错 —— 调用方的 hljs.getLanguage(lang) 返回空值，
// 自动退回到纯文本转义（见 src/markdown.js 与 LabDetailView.vue 的 hljsLanguage 判断）。
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import java from 'highlight.js/lib/languages/java'
import plaintext from 'highlight.js/lib/languages/plaintext'
import python from 'highlight.js/lib/languages/python'

// 内容里的代码围栏（```python / ```bash）与 Socket 练习编辑器
hljs.registerLanguage('python', python)
hljs.registerLanguage('bash', bash)

// ```text 是内容里最常见的围栏写法，plaintext 同时挂到 text 别名上
hljs.registerLanguage('plaintext', plaintext)
hljs.registerLanguage('text', plaintext)

// Lab 的 language 字段允许 python / c / java（见 backend/app/schemas.py），
// 一并注册，将来新增 C / Java 练习时编辑器高亮可直接生效。
hljs.registerLanguage('c', c)
hljs.registerLanguage('java', java)

export default hljs
