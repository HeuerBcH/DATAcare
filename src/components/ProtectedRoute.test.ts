import { describe, expect, it } from 'vitest';
import { homeForRole } from './ProtectedRoute';

describe('homeForRole', () => {
  it('leva gestor e admin ao dashboard', () => {
    expect(homeForRole('gestor')).toBe('/dashboard');
    expect(homeForRole('admin')).toBe('/dashboard');
  });

  it('leva ACS e profissional de saúde à triagem', () => {
    expect(homeForRole('acs')).toBe('/triagem');
    expect(homeForRole('profissional_saude')).toBe('/triagem');
  });
});
