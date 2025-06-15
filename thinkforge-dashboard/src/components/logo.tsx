

interface LogoProps {
  collapsed?: boolean
}

export function Logo({ collapsed = false }: LogoProps) {
  if (collapsed) {
    return (
      <div className="flex justify-center">
        <div className="relative w-8 h-8">
          <img src="/logo-icon.png" alt="ThinkForge Logo" width={32} height={32} className="object-contain" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center">
      <div className="relative w-8 h-8 mr-2">
        <img src="/logo-icon.png" alt="ThinkForge Logo" width={32} height={32} className="object-contain" />
      </div>
      <div>
        <div className="font-bold text-xl">
          <span className="text-blue-500">Think</span>
          <span className="text-orange-500">Forge</span>
        </div>
        <div className="text-xs text-muted-foreground leading-tight">Natural Language Cache Framework</div>
      </div>
    </div>
  )
}
