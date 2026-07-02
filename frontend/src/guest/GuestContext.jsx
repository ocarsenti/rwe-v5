import { createContext, useContext, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

const GuestCtx = createContext(null)

export function GuestProvider({ children }) {
  const [searchParams] = useSearchParams()
  const [token, setToken] = useState(() => {
    const urlToken = searchParams.get('token')
    if (urlToken) {
      sessionStorage.setItem('guest_token', urlToken)
      return urlToken
    }
    return sessionStorage.getItem('guest_token') || null
  })
  const [quota, setQuota] = useState(null) // { remaining, quota, used, name, expires }
  const [error, setError] = useState(null)

  useEffect(() => {
    const urlToken = searchParams.get('token')
    if (urlToken && urlToken !== token) {
      sessionStorage.setItem('guest_token', urlToken)
      setToken(urlToken)
    }
  }, [searchParams])

  useEffect(() => {
    if (!token) return
    fetch(`/api/guest/verify/${token}`)
      .then((r) => {
        if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || 'token_invalid') })
        return r.json()
      })
      .then(setQuota)
      .catch((e) => setError(e.message))
  }, [token])

  const refreshQuota = () => {
    if (!token) return
    fetch(`/api/guest/verify/${token}`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => d && setQuota(d))
  }

  return (
    <GuestCtx.Provider value={{ token, quota, error, refreshQuota }}>
      {children}
    </GuestCtx.Provider>
  )
}

export function useGuest() {
  return useContext(GuestCtx)
}
