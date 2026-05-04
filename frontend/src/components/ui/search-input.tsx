'use client'
import * as React from 'react'
import { Search } from 'lucide-react'
import { cn } from '@/lib/utils/format'
import { Input } from '@/components/ui/input'

export interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ value, onChange, placeholder = '검색...', className }, ref) => {
    const [localValue, setLocalValue] = React.useState(value)

    React.useEffect(() => {
      setLocalValue(value)
    }, [value])

    React.useEffect(() => {
      const timer = setTimeout(() => {
        if (localValue !== value) {
          onChange(localValue)
        }
      }, 300)
      return () => clearTimeout(timer)
    }, [localValue]) // eslint-disable-line react-hooks/exhaustive-deps

    return (
      <div className={cn('relative', className)}>
        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
        <Input
          ref={ref}
          type="search"
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          placeholder={placeholder}
          className="pl-8"
        />
      </div>
    )
  }
)
SearchInput.displayName = 'SearchInput'

export { SearchInput }
