import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const railwayNginx = readFileSync(
  resolve(process.cwd(), '../../infra/docker/railway/nginx.conf'),
  'utf8',
)

describe('Railway nginx forwarded proto', () => {
  it('relays the edge X-Forwarded-Proto instead of overwriting it with $scheme', () => {
    expect(railwayNginx).toMatch(
      /map\s+\$http_x_forwarded_proto\s+\$forwarded_proto\s*\{/,
    )
    expect(railwayNginx).toContain('""      $scheme;')
    expect(railwayNginx).not.toMatch(
      /proxy_set_header\s+X-Forwarded-Proto\s+\$scheme\s*;/,
    )
    expect(railwayNginx.match(/proxy_set_header\s+X-Forwarded-Proto\s+\$forwarded_proto\s*;/g)).toHaveLength(
      2,
    )
  })
})
