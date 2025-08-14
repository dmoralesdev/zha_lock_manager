// Minimal custom panel built with Lit. Loaded as a JS module.
// Provides CRUD of user codes via our websocket API.

/* eslint no-console: 0 */
import { LitElement, html, css } from "https://unpkg.com/lit@2.8.0/index.js?module";

class ZhaLockManagerPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
      _locks: { type: Array },
      _selected: { type: Number },
      _busy: { type: Boolean },
      _error: { type: String },
    };
  }

  constructor() {
    super();
    this._locks = [];
    this._selected = 0;
    this._busy = false;
    this._error = "";
  }

  connectedCallback() {
    super.connectedCallback();
    this._refresh();
  }

  async _ws(type, payload={}) {
    return await this.hass.callWS({ type, ...payload });
  }

  async _refresh() {
    try {
      this._busy = true;
      this._locks = await this._ws("zlm/list_locks");
      this._busy = false;
      this.requestUpdate();
    } catch (e) {
      this._busy = false;
      this._error = e?.message || String(e);
    }
  }

  get _lock() {
    if (!this._locks?.length) return null;
    return this._locks[Math.min(this._selected, this._locks.length-1)];
  }

  _slotRows(lock) {
    const rows = [];
    const max = lock.max_slots ?? 30;
    for (let i=1; i<=max; i++) {
      const key = String(i);
      const s = lock.slots?.[key] || { slot: i, label: "", enabled: false, has_code: false };
      rows.push(s);
    }
    return rows;
  }

  async _setCode(slot) {
    const code = prompt(`Enter new code for slot ${slot}`);
    if (!code) return;
    const label = prompt("Optional label for this code (name)") || "";
    try {
      this._busy = true;
      await this._ws("zlm/set_code", { device_ieee: this._lock.device_ieee, slot, code, label });
      await this._refresh();
    } catch(e) { alert("Failed: " + e); }
    finally { this._busy = false; }
  }

  async _enableDisable(slot, enable) {
    try {
      this._busy = true;
      const type = enable ? "zlm/enable_code" : "zlm/disable_code";
      await this._ws(type, { device_ieee: this._lock.device_ieee, slot });
      await this._refresh();
    } catch(e) { alert("Failed: " + e); }
    finally { this._busy = false; }
  }

  async _clear(slot) {
    if (!confirm(`Clear code at slot ${slot}?`)) return;
    try {
      this._busy = true;
      await this._ws("zlm/clear_code", { device_ieee: this._lock.device_ieee, slot });
      await this._refresh();
    } catch(e) { alert("Failed: " + e); }
    finally { this._busy = false; }
  }

  async _saveMeta() {
    const name = this.renderRoot.querySelector("#name").value;
    const max_slots = parseInt(this.renderRoot.querySelector("#max").value || "30");
    const slot_offset = parseInt(this.renderRoot.querySelector("#offset").value || "0");
    try {
      this._busy = true;
      await this._ws("zlm/save_lock_meta", { device_ieee: this._lock.device_ieee, name, max_slots, slot_offset });
      await this._refresh();
    } catch(e) { alert("Failed: " + e); }
    finally { this._busy = false; }
  }

  render() {
    const lock = this._lock;
    return html`
      <div class="wrap">
        <div class="header">
          <h2>🗝️ ZHA Lock Manager</h2>
          <ha-button @click=${() => this._refresh()} ?disabled=${this._busy}>Refresh</ha-button>
        </div>
        ${this._error ? html`<div class="err">${this._error}</div>` : ""}
        <div class="cols">
          <div class="left">
            <div class="card">
              <h3>Locks</h3>
              <ul class="list">
                ${this._locks.map((l, idx) => html`
                  <li class="${idx===this._selected? 'sel': ''}" @click=${() => { this._selected = idx; this.requestUpdate(); }}>
                    <div class="name">${l.name}</div>
                    <div class="sub">${l.entity_id} · ${l.device_ieee}</div>
                  </li>
                `)}
              </ul>
            </div>
          </div>
          <div class="right">
            ${lock ? html`
              <div class="card">
                <h3>Lock: ${lock.name}</h3>
                <div class="meta">
                  <label>Name <input id="name" .value=${lock.name}></label>
                  <label>Max slots <input id="max" type="number" min="1" max="250" .value=${String(lock.max_slots||30)}></label>
                  <label>Slot offset <input id="offset" type="number" .value=${String(lock.slot_offset||0)}></label>
                  <ha-button @click=${() => this._saveMeta()} ?disabled=${this._busy}>Save</ha-button>
                </div>
              </div>
              <div class="card">
                <h3>Slots</h3>
                <table class="slots">
                  <thead><tr><th>#</th><th>Label</th><th>Status</th><th>Actions</th></tr></thead>
                  <tbody>
                    ${this._slotRows(lock).map((s) => html`
                      <tr>
                        <td>${s.slot}</td>
                        <td>${s.label||''}</td>
                        <td>${s.has_code ? (s.enabled ? 'Enabled' : 'Disabled') : 'Empty'}</td>
                        <td>
                          <ha-button @click=${() => this._setCode(s.slot)} ?disabled=${this._busy}>Set</ha-button>
                          <ha-button @click=${() => this._enableDisable(s.slot, true)} ?disabled=${this._busy || !s.has_code}>Enable</ha-button>
                          <ha-button @click=${() => this._enableDisable(s.slot, false)} ?disabled=${this._busy || !s.has_code}>Disable</ha-button>
                          <ha-button @click=${() => this._clear(s.slot)} ?disabled=${this._busy || !s.has_code}>Clear</ha-button>
                        </td>
                      </tr>
                    `)}
                  </tbody>
                </table>
              </div>
            ` : html`<div class="card">No locks configured in integration options.</div>`}
          </div>
        </div>
      </div>
    `;
  }

  static get styles() {
    return css`
      :host { display:block; padding:16px; }
      .wrap { max-width: 1200px; margin: 0 auto; }
      .header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 16px; }
      .cols { display: grid; grid-template-columns: 320px 1fr; gap: 16px; }
      .card { background: var(--card-background-color); border-radius: 16px; padding: 16px; box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,0.12)); }
      h3 { margin: 0 0 12px; }
      ul.list { list-style: none; margin: 0; padding: 0; }
      ul.list li { padding: 10px; border-radius: 12px; cursor: pointer; }
      ul.list li:hover { background: rgba(0,0,0,0.05); }
      ul.list li.sel { background: rgba(0,0,0,0.1); }
      .name { font-weight: 600; }
      .sub { font-size: 12px; opacity: 0.7; }
      .meta label { display: inline-flex; flex-direction: column; margin-right: 12px; }
      table.slots { width: 100%; border-collapse: collapse; }
      table.slots th, table.slots td { padding: 8px; border-bottom: 1px solid rgba(0,0,0,0.08); }
      ha-button { margin-right: 6px; }
      .err { background:#ffebee; color:#b71c1c; padding:8px 12px; border-radius:12px; margin-bottom:8px; }
      @media (max-width: 900px) { .cols { grid-template-columns: 1fr; } }
    `;
  }
}

customElements.define("zha-lock-manager-panel", ZhaLockManagerPanel);


// Expose a dummy class name to satisfy panel registration
export default ZhaLockManagerPanel;