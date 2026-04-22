import { useEffect, useState } from 'react'
import { Shield, Users } from 'lucide-react'
import { adminApi, AdminUser } from '../api/client'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

export default function Admin() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadUsers()
  }, [])

  async function loadUsers() {
    setLoading(true)
    setError(null)
    const response = await adminApi.listUsers()
    if (response.data) {
      setUsers(response.data)
    } else {
      setError(response.error || 'Unable to load users.')
    }
    setLoading(false)
  }

  async function toggleRole(user: AdminUser) {
    const nextRole = user.role === 'admin' ? 'user' : 'admin'
    setUpdatingUserId(user.id)
    const response = await adminApi.updateUserRole(user.id, nextRole)
    if (response.data) {
      setUsers((current) => current.map((item) => (item.id === user.id ? response.data! : item)))
      setError(null)
    } else {
      setError(response.error || 'Unable to update user role.')
    }
    setUpdatingUserId(null)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-indigo-600">Admin Console</p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Users and Roles</h1>
          <p className="mt-2 text-slate-600">
            This is the first admin-only surface. It proves the RBAC wiring before Greenhouse sources land.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
          <Shield className="h-4 w-4" />
          Admin-only route
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total users</CardDescription>
            <CardTitle>{users.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Admins</CardDescription>
            <CardTitle>{users.filter((user) => user.role === 'admin').length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="border-slate-200/80">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Users className="h-5 w-5 text-slate-500" />
            <div>
              <CardTitle className="text-xl">Access Control</CardTitle>
              <CardDescription>Promote or demote users as the product grows.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          {loading ? (
            <div className="flex items-center gap-3 py-8 text-sm text-slate-500">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700"></div>
              Loading users...
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">User</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">Role</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-500">Last Login</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-500">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-4 py-4">
                        <div className="font-medium text-slate-900">{user.name || user.email}</div>
                        <div className="text-slate-500">{user.email}</div>
                      </td>
                      <td className="px-4 py-4">
                        <Badge variant={user.role === 'admin' ? 'success' : 'secondary'}>
                          {user.role}
                        </Badge>
                      </td>
                      <td className="px-4 py-4 text-slate-500">
                        {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={updatingUserId === user.id}
                          onClick={() => toggleRole(user)}
                        >
                          {updatingUserId === user.id
                            ? 'Updating...'
                            : user.role === 'admin'
                              ? 'Make User'
                              : 'Make Admin'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
