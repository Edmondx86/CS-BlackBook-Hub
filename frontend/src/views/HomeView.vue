<script setup>
// 首页大厅：欢迎标语 + 计算机知识卡片 + 「开始探索」按钮。
// 章节与实验入口已迁移到 /chapters 与 /chapters/:chapterId。

const knowledgeCards = [
  { icon: '🌐', title: '应用层', desc: 'HTTP / DNS 与 Socket 编程' },
  { icon: '🔗', title: '传输层', desc: 'TCP 可靠传输与 UDP' },
  { icon: '📦', title: '网络层', desc: 'IP 编址与分组转发' },
  { icon: '📡', title: '链路层', desc: 'MAC、ARP 与以太网' },
  { icon: '🧭', title: '协议分层', desc: '自顶向下的抽象思想' },
  { icon: '🛠️', title: 'Wireshark', desc: '抓包分析与实战实验' },
]
</script>

<template>
  <div class="h-full overflow-y-auto bg-zinc-950">
    <div class="mx-auto flex min-h-full max-w-4xl flex-col justify-center px-6 py-16">
      <!-- 欢迎标语 -->
      <section class="text-center">
        <p class="text-sm font-semibold uppercase tracking-widest text-sky-400">
          Computer Networking · A Top-Down Approach
        </p>
        <h1 class="mt-3 text-4xl font-bold tracking-tight text-white sm:text-5xl">
          计算机网络 · 自顶向下
        </h1>
        <p class="mx-auto mt-4 max-w-xl text-zinc-400">
          从应用层出发，逐层深入传输层、网络层与链路层，配套 Wireshark 抓包实验与 Socket 在线判题。
        </p>
      </section>

      <!-- 计算机知识卡片 -->
      <section class="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="card in knowledgeCards"
          :key="card.title"
          class="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 transition hover:border-zinc-700 hover:bg-zinc-900/70"
        >
          <div class="text-2xl">{{ card.icon }}</div>
          <h3 class="mt-3 font-semibold text-white">{{ card.title }}</h3>
          <p class="mt-1 text-sm text-zinc-400">{{ card.desc }}</p>
        </div>
      </section>

      <!-- 开始探索按钮 -->
      <div class="mt-12 text-center">
        <RouterLink
          to="/chapters"
          class="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-sky-500"
        >
          开始探索
          <span aria-hidden="true">→</span>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
