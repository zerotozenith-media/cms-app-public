import { useNavigate } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';

import { useState } from 'react';
import { useMyLocations } from '../../api/locations';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

/** P10: phones the form is refusing today, and a way to let them in. */
function Blocks() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ['registration-blocks'],
    queryFn: async () => (await apiClient.get<{ results: { ip: string; device_id: string; refused: number; last: string; still_blocked: boolean }[]; per_phone: number }>('/newcomers-registration-blocks/')).data,
  });
  const lift = useMutation({
    mutationFn: async (b: { ip: string; device_id: string }) => (await apiClient.post('/newcomers-registration-blocks/', b.device_id ? { device_id: b.device_id } : { ip: b.ip })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['registration-blocks'] }),
  });
  const rows = (data?.results ?? []).filter((r) => r.still_blocked);
  return (
    <div className="card section-gap" style={{ maxWidth: 480, margin: '16px auto 0' }}>
      <h3 style={{ margin: '0 0 4px' }}>Phones turned away today</h3>
      <p className="muted" style={{ fontSize: '.82rem', margin: '0 0 8px' }}>
        Each phone can send {data?.per_phone ?? 5} forms a day, enough for a family. Visitors on the church Wi-Fi are counted phone by phone, so they never block each other.
      </p>
      {rows.length === 0 ? <div className="muted" style={{ fontSize: '.86rem' }}>None.</div> : rows.map((r) => (
        <div key={`${r.ip}-${r.device_id}`} className="person-row" style={{ fontSize: '.84rem' }}>
          <span>{r.device_id ? `Phone ${r.device_id.slice(-6)}` : `Address ${r.ip}`} <span className="muted">· turned away {r.refused} time{r.refused === 1 ? '' : 's'}</span></span>
          <button className="btn sm outline" onClick={() => lift.mutate(r)} disabled={lift.isPending}>Let them in</button>
        </div>
      ))}
    </div>
  );
}
export function QrRegistrationPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  // One code per location, so a visitor lands in the pipeline of the
  // location they attended rather than always the main one.
  const { data: locations } = useMyLocations();
  const [chosen, setChosen] = useState('');
  const main = locations?.find((l) => l.is_core) ?? locations?.[0];
  const location = locations?.find((l) => l.id === chosen) ?? main;
  const registrationUrl = `${window.location.origin}/register${location ? `?location=${location.id}` : ''}`;

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/newcomers')}>Pipeline</button>
          <button className="tab" onClick={() => navigate('/newcomers/follow-up')}>Follow-up</button>
          <button className="tab" onClick={() => navigate('/newcomers/messages')}>Messages</button>
          <button className="tab active">QR Registration</button>
          <button className="tab" onClick={() => navigate('/newcomers/manual')}>Manual Entry</button>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480, textAlign: 'center', margin: '0 auto' }}>
        <h3>Project this during the newcomer announcement</h3>
        <p className="muted">
          Newcomers scan this with their phone camera to fill in the welcome form themselves. Each
          submission lands in the New column of the location this code is for, tagged with the source
          "Church website (QR self-registration)".
        </p>
        {(locations ?? []).length > 1 && (
          <div className="field" style={{ maxWidth: 260, margin: '0 auto', textAlign: 'left' }}>
            <label htmlFor="qr-location">Code for</label>
            <select id="qr-location" value={location?.id ?? ''} onChange={(e) => setChosen(e.target.value)}>
              {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
        )}
        {location && <div style={{ fontWeight: 700, marginTop: 10 }}>For visitors at {location.name}</div>}
        <div style={{ margin: '16px auto', border: '1px solid var(--line)', borderRadius: 10, padding: 16, display: 'inline-block' }}>
          <QRCodeSVG value={registrationUrl} size={200} />
        </div>
        <div className="muted" style={{ fontSize: '.8rem', wordBreak: 'break-all' }}>{registrationUrl}</div>
      </div>
      {hasPermission('newcomers', 'edit') && hasPermission('admin', 'view') && <Blocks />}
    </>
  );
}
