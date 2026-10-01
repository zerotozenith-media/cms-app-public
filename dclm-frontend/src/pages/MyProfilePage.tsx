import { MyServiceCard } from '../components/service/ServiceBadge';
import { useEffect, useRef, useState } from 'react';
import { apiClient, mediaUrl } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

interface Profile {
  first_name: string; last_name: string; name: string; email: string; phone: string;
  photo: string | null; role: string | null; location_name: string | null;
}

export function initialsOf(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
}

/** F3: each person manages their own account. Role and location stay with administrators. */
export function MyProfilePage() {
  const { updateUser } = useAuth();
  const [p, setP] = useState<Profile | null>(null);
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });
  const [saved, setSaved] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pw, setPw] = useState({ current_password: '', new_password: '', new_password_again: '' });
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function apply(data: Profile) {
    setP(data);
    setForm({ first_name: data.first_name, last_name: data.last_name, phone: data.phone, email: data.email });
    updateUser({ name: data.name, email: data.email, photo: data.photo });
  }
  useEffect(() => { apiClient.get('/auth/me/').then((r) => apply(r.data)); }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  function firstError(d: any) {
    const out: Record<string, string> = {};
    Object.entries(d ?? {}).forEach(([k, v]) => { out[k] = Array.isArray(v) ? String(v[0]) : String(v); });
    return out;
  }

  async function saveDetails(e: React.FormEvent) {
    e.preventDefault();
    setErrors({}); setSaved(null); setBusy(true);
    try { apply((await apiClient.patch('/auth/me/', form)).data); setSaved('Saved.'); }
    catch (err: any) { setErrors(firstError(err?.response?.data)); }
    finally { setBusy(false); }
  }

  async function upload(file: File) {
    setErrors({}); setBusy(true);
    const body = new FormData(); body.append('photo', file);
    try { apply((await apiClient.post('/auth/me/photo/', body, { headers: { 'Content-Type': 'multipart/form-data' } })).data); }
    catch (err: any) { setErrors(firstError(err?.response?.data)); }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = ''; }
  }

  async function removePhoto() {
    setBusy(true);
    try { apply((await apiClient.delete('/auth/me/photo/')).data); } finally { setBusy(false); }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwMsg(null);
    try {
      await apiClient.post('/auth/me/password/', pw);
      setPw({ current_password: '', new_password: '', new_password_again: '' });
      setPwMsg({ ok: true, text: 'Password changed.' });
    } catch (err: any) {
      const d = firstError(err?.response?.data);
      setPwMsg({ ok: false, text: d.current_password ?? d.new_password_again ?? d.new_password ?? 'Could not change the password.' });
    }
  }

  if (!p) return <Card><p className="muted">Loading your profile…</p></Card>;
  return (
    <div className="profile-page">
      <Card>
        <div className="me-photo-row">
          {p.photo
            ? <img className="me-photo" src={mediaUrl(p.photo) ?? ''} alt={p.name} />
            : <div className="me-photo me-initials">{initialsOf(p.name)}</div>}
          <div>
            <input ref={fileRef} type="file" accept="image/*" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); }} />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button type="button" onClick={() => fileRef.current?.click()} disabled={busy}>
                {p.photo ? 'Change photo' : 'Add a photo'}
              </Button>
              {p.photo && <Button type="button" variant="outline" onClick={removePhoto} disabled={busy}>Remove</Button>}
            </div>
            <div className="muted" style={{ fontSize: '.8rem', marginTop: 6 }}>A picture from your phone or computer. It shows wherever the app shows you.</div>
            {errors.photo && <p className="form-error">{errors.photo}</p>}
          </div>
        </div>

        <form onSubmit={saveDetails} style={{ marginTop: 18 }}>
          <div className="form-row">
            <div className="field"><label htmlFor="me-first">First name</label>
              <input id="me-first" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
              {errors.first_name && <p className="form-error">{errors.first_name}</p>}</div>
            <div className="field"><label htmlFor="me-last">Last name</label>
              <input id="me-last" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div>
          </div>
          <div className="form-row">
            <div className="field"><label htmlFor="me-phone">Phone</label>
              <input id="me-phone" type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="field"><label htmlFor="me-email">Email</label>
              <input id="me-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              {errors.email && <p className="form-error">{errors.email}</p>}</div>
          </div>
          <p className="muted" style={{ fontSize: '.82rem' }}>
            Role: <b>{p.role ?? 'None'}</b> · Location: <b>{p.location_name ?? 'All locations'}</b>. An administrator sets these.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button type="submit" disabled={busy}>Save changes</Button>
            {saved && <span className="muted" role="status">{saved}</span>}
          </div>
        </form>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <h3>Change password</h3>
        <form onSubmit={changePassword}>
          <div className="field"><label htmlFor="me-current">Current password</label>
            <input id="me-current" type="password" autoComplete="current-password" value={pw.current_password}
              onChange={(e) => setPw({ ...pw, current_password: e.target.value })} required /></div>
          <div className="form-row">
            <div className="field"><label htmlFor="me-new">New password</label>
              <input id="me-new" type="password" autoComplete="new-password" value={pw.new_password}
                onChange={(e) => setPw({ ...pw, new_password: e.target.value })} required /></div>
            <div className="field"><label htmlFor="me-new-again">New password again</label>
              <input id="me-new-again" type="password" autoComplete="new-password" value={pw.new_password_again}
                onChange={(e) => setPw({ ...pw, new_password_again: e.target.value })} required /></div>
          </div>
          <p className="muted" style={{ fontSize: '.8rem' }}>At least 10 characters, not only numbers, not a common password, and not too like your name or email.</p>
          {pwMsg && <p className={pwMsg.ok ? 'muted' : 'form-error'} role="status">{pwMsg.text}</p>}
          <Button type="submit">Change password</Button>
        </form>
      </Card>
      <MyServiceCard />
    </div>
  );
}
