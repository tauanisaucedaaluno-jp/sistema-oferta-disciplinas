import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Previne crashes de 'Failed to execute removeChild on Node' causados pelo Google Tradutor ou extensões do navegador
if (typeof Node === 'function' && Node.prototype) {
  const originalRemoveChild = Node.prototype.removeChild
  Node.prototype.removeChild = function <T extends Node>(child: T): T {
    if (child.parentNode !== this) {
      if (typeof console !== 'undefined') {
        console.warn('Proteção ativada: nó ignorado pois não é mais filho direto deste elemento (Google Tradutor/Extensão detectado).', child, this)
      }
      return child
    }
    return originalRemoveChild.apply(this, [child]) as T
  }

  const originalInsertBefore = Node.prototype.insertBefore
  Node.prototype.insertBefore = function <T extends Node>(newNode: T, referenceNode: Node | null): T {
    if (referenceNode && referenceNode.parentNode !== this) {
      if (typeof console !== 'undefined') {
        console.warn('Proteção ativada: inserção antes de referência ignorada pois não é filho direto deste elemento.', referenceNode, this)
      }
      return newNode
    }
    return originalInsertBefore.apply(this, [newNode, referenceNode]) as T
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
