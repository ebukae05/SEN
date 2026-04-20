'use client'

import { useEffect, useRef } from 'react'
import { Brain, Cpu, Zap, Activity } from 'lucide-react'

// Neural network visualization
function NeuralVisualization() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = 500
    const height = 400
    canvas.width = width
    canvas.height = height

    interface Node {
      x: number
      y: number
      vx: number
      vy: number
      size: number
      connections: number[]
      pulsePhase: number
    }

    // Create neural network nodes
    const nodes: Node[] = []
    const nodeCount = 50

    for (let i = 0; i < nodeCount; i++) {
      const angle = (i / nodeCount) * Math.PI * 2
      const radius = 80 + Math.random() * 100
      nodes.push({
        x: width / 2 + Math.cos(angle) * radius + (Math.random() - 0.5) * 60,
        y: height / 2 + Math.sin(angle) * radius * 0.7 + (Math.random() - 0.5) * 40,
        vx: (Math.random() - 0.5) * 0.2,
        vy: (Math.random() - 0.5) * 0.2,
        size: Math.random() * 3 + 2,
        connections: [],
        pulsePhase: Math.random() * Math.PI * 2,
      })
    }

    // Create connections
    nodes.forEach((node, i) => {
      const connectionCount = Math.floor(Math.random() * 3) + 1
      for (let c = 0; c < connectionCount; c++) {
        const target = Math.floor(Math.random() * nodeCount)
        if (target !== i) {
          node.connections.push(target)
        }
      }
    })

    let time = 0

    const animate = () => {
      ctx.clearRect(0, 0, width, height)
      time += 0.02

      // Update and draw connections
      nodes.forEach((node, i) => {
        node.x += node.vx
        node.y += node.vy

        // Gentle boundary bounce
        if (node.x < 50 || node.x > width - 50) node.vx *= -1
        if (node.y < 50 || node.y > height - 50) node.vy *= -1

        // Draw connections with animated pulse
        node.connections.forEach(targetIdx => {
          const target = nodes[targetIdx]
          const gradient = ctx.createLinearGradient(node.x, node.y, target.x, target.y)
          
          const pulsePos = (Math.sin(time * 2 + node.pulsePhase) + 1) / 2
          gradient.addColorStop(0, 'rgba(59, 130, 246, 0.1)')
          gradient.addColorStop(pulsePos, 'rgba(59, 130, 246, 0.4)')
          gradient.addColorStop(1, 'rgba(96, 165, 250, 0.1)')

          ctx.beginPath()
          ctx.moveTo(node.x, node.y)
          ctx.lineTo(target.x, target.y)
          ctx.strokeStyle = gradient
          ctx.lineWidth = 1
          ctx.stroke()
        })
      })

      // Draw nodes with glow
      nodes.forEach((node) => {
        const pulse = Math.sin(time * 2 + node.pulsePhase) * 0.3 + 0.7
        
        // Glow
        const gradient = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, node.size * 4
        )
        gradient.addColorStop(0, `rgba(59, 130, 246, ${0.4 * pulse})`)
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0)')
        
        ctx.beginPath()
        ctx.arc(node.x, node.y, node.size * 4, 0, Math.PI * 2)
        ctx.fillStyle = gradient
        ctx.fill()

        // Core
        ctx.beginPath()
        ctx.arc(node.x, node.y, node.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(59, 130, 246, ${0.8 * pulse})`
        ctx.fill()
      })

      requestAnimationFrame(animate)
    }

    const animationId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationId)
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="mx-auto"
      style={{ maxWidth: '100%', height: 'auto' }}
    />
  )
}

export function HomeView() {
  return (
    <div className="flex flex-col items-center justify-center min-h-full py-12 px-8">
      {/* Hero section */}
      <div className="text-center mb-8">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-4">
          Artificial Engine Intelligence
        </p>
        <h1 className="text-6xl font-bold tracking-tight text-foreground mb-2 glow-navy">
          SEN
        </h1>
        <p className="text-muted-foreground text-lg">Sensor Engine Network</p>
      </div>

      {/* Neural visualization */}
      <div className="relative mb-12">
        <NeuralVisualization />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent pointer-events-none" />
      </div>

      {/* Problem & Solution */}
      <div className="max-w-4xl grid md:grid-cols-2 gap-8 mb-12">
        <div className="p-6 rounded-xl bg-card/50 border border-border glow-border">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 rounded-lg bg-status-critical/20">
              <Zap className="w-5 h-5 text-status-critical" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">The Problem</h2>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Aircraft engine maintenance is overwhelmingly reactive or calendar-based. 
            Engines get pulled from service on fixed schedules regardless of actual condition, 
            leading to unnecessary maintenance on healthy engines, missed early warnings that 
            cause in-flight shutdowns, and $10K-$50K+ per hour in Aircraft on Ground (AOG) costs.
          </p>
        </div>

        <div className="p-6 rounded-xl bg-card/50 border border-border glow-border">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 rounded-lg bg-primary/20">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">The Solution</h2>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            SEN uses a multi-agent AI pipeline (built with CrewAI) to ingest live sensor data 
            from turbofan engines, run predictions through a CNN-LSTM deep learning model, 
            diagnose degradation patterns, and generate actionable maintenance recommendations 
            — all in real time. It shifts maintenance from time-based to condition-based.
          </p>
        </div>
      </div>

      {/* Key capabilities */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl w-full">
        {[
          {
            icon: Activity,
            title: 'Condition-Based',
            description: 'Shifts maintenance from time-based to condition-based monitoring',
          },
          {
            icon: Cpu,
            title: 'Multi-Agent AI',
            description: 'CNN-LSTM deep learning pipeline with CrewAI orchestration',
          },
          {
            icon: Zap,
            title: 'Real-Time RUL',
            description: 'Predict Remaining Useful Life across fleets of 100+ engines',
          },
        ].map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.title}
              className="p-4 rounded-lg bg-secondary/30 border border-border/50 text-center hover:bg-secondary/50 transition-colors"
            >
              <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-primary/10 flex items-center justify-center">
                <Icon className="w-5 h-5 text-primary" />
              </div>
              <h3 className="font-medium text-foreground mb-1">{item.title}</h3>
              <p className="text-xs text-muted-foreground">{item.description}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
