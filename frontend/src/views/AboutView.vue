<script setup>
// 关于页：内嵌 m4tt72/terminal（终端风格），铺满整个内容区（只保留全局页头）。
//
// 终端静态文件全部在 frontend/public/terminal/，由 Vite 原样拷进 dist/terminal/，
// 所以**这个目录是运行时依赖，必须进仓库**（丢了这一页就是白屏）。
// 其中 8 个文件 = 上游构建产物 5 个 + 手工放的 3 个（config.json / banner.txt / p.txt，
// 三者都是运行时 fetch 的）；重建步骤见本文件末尾注释。
//
// ────────────────────────── 中文对齐补丁 ──────────────────────────
// 终端会把命令输出套一个文本框（┌─┐ / │ / └─┘），宽度按“中文 = 2 格”来补空格，
// 而且它自己的宽度函数算得没错（Ve 判宽字符 / Ae 求宽度 / qe 按宽度补空格）。
// 对不齐的真正原因在字体度量：
//
//     Cascadia Code 的拉丁字宽 = 1200 / 2048 = 0.5859 em  →  2 格 = 1.1719 em
//     中文回退字体是全角                        = 1.0000 em  →  只占 1.707 格
//
// 于是每多一个中文，右边框就比预期少 0.293 格；一行几十个中文累积下来就明显歪了。
// 修法：给中文单独定义一个 @font-face 并用 size-adjust 放大到 1.1719 em（117.2%），
// 让中文正好占 2 格，方框自然对齐。
//
// 为什么写在这里、而不是去改终端的 CSS：terminal/ 是第三方构建产物（压缩过，
// 一重建就没了）。注入的方式让补丁留在我们自己的仓库里 —— **将来重建终端它依然生效**。
const TERMINAL_URL = '/terminal/index.html'

const CJK_ALIGN_FIX = `
@font-face {
  font-family: 'CSBB Mono CJK';
  src: local('NSimSun'), local('SimSun'), local('Sarasa Mono SC'),
       local('Noto Sans Mono CJK SC'), local('Microsoft YaHei'), local('PingFang SC');
  size-adjust: 117.2%;
  font-display: swap;
  /* 关键：覆盖范围必须与终端自己的宽度函数 Ve() 完全一致。
     若不加 unicode-range，Cascadia 缺失的西文标点（比如技能行里的 ·）也会回退到这个
     被放大 117.2% 的字体上，于是“按 1 格算、实际占 2 格”，反而向另一个方向错位
     （实测那行会多出正好 1 格 = 9.4px）。这里把范围对齐 Ve() 判定的宽字符区间，
     宽字符走放大字体、其余字符走 Cascadia/monospace，两边就一致了。 */
  unicode-range: U+1100-115F, U+2E80-A4CF, U+AC00-D7A3, U+F900-FAFF,
                 U+FE30-FE4F, U+FF00-FF60, U+FFE0-FFE6;
}
html, body, body * {
  font-family: 'Cascadia Code', 'CSBB Mono CJK', monospace !important;
}
`

function applyCjkFix(event) {
  // iframe 与本站同源，可以直接操作它的文档
  const doc = event.target?.contentDocument
  if (!doc?.head) return
  const style = doc.createElement('style')
  style.textContent = CJK_ALIGN_FIX
  doc.head.appendChild(style)
}

// 重建终端（仅在需要改终端页时）：
//   git clone https://github.com/m4tt72/terminal → npm i && npm run build
//   → 把 dist/ 覆盖到 frontend/public/terminal/
//   → 再把 config.json / banner.txt / p.txt 三个文件放回去（上游构建不产出它们）
//   线上 banner.txt 与上游 src/banner.txt 已不同步（横幅是在这里改的）
</script>

<template>
  <div class="h-full w-full">
    <iframe
      :src="TERMINAL_URL"
      title="终端"
      class="block h-full w-full border-0 bg-card"
      @load="applyCjkFix"
    ></iframe>
  </div>
</template>
