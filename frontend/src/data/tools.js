// 首页“常见工具”四个工具的统一数据源：首页卡片与工具介绍页共用，
// 避免两份标题/描述/图标不一致。slug 用于路由 /tools/:slug，
// 对应 src/content/tools/<slug>.md 里的详细介绍正文。
export const tools = [
  {
    slug: 'diagnostics',
    title: '网络诊断工具',
    subtitle: 'ping · traceroute · La/R',
    desc: 'ping、traceroute、流量强度 La/R 分析，快速定位时延、丢包与瓶颈链路。',
    route: '/tools/diagnostics',
    icon: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>',
  },
  {
    slug: 'wireshark',
    title: 'Wireshark',
    subtitle: 'Packet Capture & Protocol Analysis',
    desc: '网络抓包分析利器，逐层拆解 HTTP、DNS、TCP 报文，跟着官方 Lab 一步步验证协议行为。',
    route: '/tools/wireshark',
    icon: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>',
    // 官方链接（工具页会渲染成外链按钮；没有 links 的工具不显示这一块）
    links: [
      { label: 'Wireshark 官网', url: 'https://www.wireshark.org/' },
      { label: '下载 Wireshark', url: 'https://www.wireshark.org/download.html' },
    ],
  },
  {
    slug: 'socket',
    title: 'Socket 编程',
    subtitle: 'Online Sandbox & Auto-Grading',
    desc: '内置在线沙盒与自动化评测，客户端 / 服务器代码即写即测，边学边练。',
    route: '/tools/socket',
    icon: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>',
  },
  {
    slug: 'cisco',
    title: 'Cisco Packet Tracer',
    subtitle: 'Network Topology Simulation',
    desc: '网络拓扑仿真环境，拖拽搭建路由器与交换机，直观模拟分组转发全过程。',
    route: '/tools/cisco',
    icon: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>',
    // 官方链接（工具页会渲染成外链按钮；没有 links 的工具不显示这一块）
    links: [
      { label: 'Cisco Packet Tracer 官方页面', url: 'https://www.netacad.com/cisco-packet-tracer' },
    ],
  },
]
