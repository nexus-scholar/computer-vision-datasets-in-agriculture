import './input.css'
import htmx from 'htmx.org'

document.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target.id === 'tab-content') {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'))
    if (e.detail.elt?.classList?.contains('tab-btn')) {
      e.detail.elt.classList.add('active')
    }
  }
  const ov = document.getElementById('data-timestamp')
  if (e.detail.target.id === 'overview' && ov) {
    ov.textContent = new Date().toISOString()
  }
})

document.addEventListener('click', (e) => {
  const link = e.target.closest('.paper-link')
  if (!link) return
  e.preventDefault()
  const rank = link.getAttribute('data-rank')
  if (!rank) return
  htmx.ajax('GET', `/api/paper/${rank}`, { target: '#drawer-content', swap: 'innerHTML' })
  openDrawer()
})

function openDrawer() {
  const overlay = document.getElementById('drawer-overlay')
  const panel = document.getElementById('drawer-panel')
  overlay?.classList.remove('hidden')
  panel?.classList.remove('translate-x-full')
}

window.closeDrawer = function closeDrawer() {
  const overlay = document.getElementById('drawer-overlay')
  const panel = document.getElementById('drawer-panel')
  overlay?.classList.add('hidden')
  panel?.classList.add('translate-x-full')
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') window.closeDrawer()
})
