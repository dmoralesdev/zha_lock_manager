/* ZHA Lock Manager panel, Lit-based custom panel */
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
    this._onResize = () => this.requestUpdate();
  }

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("resize", this._onResize);
    this._refresh();
  }

  disconnectedCallback() {
    window.removeEventListener("resize", this._onResize);
    super.disconnectedCallback();
  }

  get isMobile() {
    return this.narrow || window.innerWidth <= 820;
  }

  async _ws(type, payload = {}) {
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
    return this._locks[Math.min(this._selected, this._locks.length - 1)];
  }

  _slotRows(lock) {
    const rows = [];
    const max = lock.max_slots ?? 30;
    for (let i = 1; i <= max; i++) {
      const key = String(i);
      const s = lock.slots?.[key] || { slot: i, label: "", enabled: false, has_code: false };
      rows.push(s);
    }
    return rows;
  }

  async _setCode(slot) {
    const code = prompt(`Enter new code for slot ${slot}`);
    if (!code) return;
    const label = prompt("Optional label for this code") || "";
    try {
      this._busy = true;
      await this._ws("zlm/set_code", { device_ieee: this._lock.device_ieee, slot, code, label });
      await this._refresh();
    } catch (e) {
      alert("Failed: " + e);
    } finally {
      this._busy = false;
    }
  }

  async _toggle(slot) {
    const s = this._lock?.slots?.[String(slot)];
    if (!s || !s.has_code) return;
    const enable = !s.enabled;
    try {
      this._busy = true;
      const type = enable ? "zlm/enable_code" : "zlm/disable_code";
      await this._ws(type, { device_ieee: this._lock.device_ieee, slot });
      await this._refresh();
    } catch (e) {
      alert("Failed: " + e);
    } finally {
      this._busy = false;
    }
  }

  async _clear(slot) {
    if (!confirm(`Clear code at slot ${slot}?`)) return;
    try {
      this._busy = true;
      await this._ws("zlm/clear_code", { device_ieee: this._lock.device_ieee, slot });
      await this._refresh();
    } catch (e) {
      alert("Failed: " + e);
    } finally {
      this._busy = false;
    }
  }

  async _saveMeta() {
    const name = this.renderRoot.querySelector("#name").value;
    const max_slots = parseInt(this.renderRoot.querySelector("#max").value || "30");
    const slot_offset = parseInt(this.renderRoot.querySelector("#offset").value || "0");
    try {
      this._busy = true;
      await this._ws("zlm/save_lock_meta", {
        device_ieee: this._lock.device_ieee,
        name,
        max_slots,
        slot_offset,
      });
      await this._refresh();
    } catch (e) {
      alert("Failed: " + e);
    } finally {
      this._busy = false;
    }
  }

  /* Desktop slots table, column order: Slot, Status, Name, Actions */
  _renderSlotsDesktop(lock) {
    return html`
      <div class="card">
        <h3>Slots</h3>
        <table class="slots">
          <thead>
            <tr>
              <th class="col-num">Slot</th>
              <th class="col-status">Status</th>
              <th class="col-label">Name</th>
              <th class="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${this._slotRows(lock).map((s) => {
              const status = s.has_code ? (s.enabled ? "Enabled" : "Disabled") : "Empty";
              const toggleLabel = s.enabled ? "Disable" : "Enable";
              return html`
                <tr>
                  <td>${s.slot}</td>
                  <td>${status}</td>
                  <td>${s.label || ""}</td>
                  <td class="col-actions">
                    <div class="btn-grid">
                      <ha-button class="action" @click=${() => this._setCode(s.slot)} ?disabled=${this._busy}>
                        Set
                      </ha-button>
                      <ha-button
                        class="action"
                        @click=${() => this._toggle(s.slot)}
                        ?disabled=${this._busy || !s.has_code}
                      >
                        ${toggleLabel}
                      </ha-button>
                      <ha-button
                        class="action"
                        @click=${() => this._clear(s.slot)}
                        ?disabled=${this._busy || !s.has_code}
                      >
                        Clear
                      </ha-button>
                    </div>
                  </td>
                </tr>
              `;
            })}
          </tbody>
        </table>
      </div>
    `;
  }

  /* Mobile stacked layout, texts centered above equal-width buttons */
  _renderSlotsMobile(lock) {
    return html`
      <div class="card">
        <h3>Slots</h3>
        <div class="mobile-slots">
          ${this._slotRows(lock).map((s) => {
            const status = s.has_code ? (s.enabled ? "Enabled" : "Disabled") : "Empty";
            const toggleLabel = s.enabled ? "Disable" : "Enable";
            return html`
              <div class="mrow">
                <div class="mhead">
                  <div class="mcell mnum">#${s.slot}</div>
                  <div class="mcell mstatus">${status}</div>
                  <div class="mcell mlabel">${s.label || ""}</div>
                </div>
                <div class="mactions btn-grid">
                  <ha-button class="action" @click=${() => this._setCode(s.slot)} ?disabled=${this._busy}>
                    Set
                  </ha-button>
                  <ha-button
                    class="action"
                    @click=${() => this._toggle(s.slot)}
                    ?disabled=${this._busy || !s.has_code}
                  >
                    ${toggleLabel}
                  </ha-button>
                  <ha-button
                    class="action"
                    @click=${() => this._clear(s.slot)}
                    ?disabled=${this._busy || !s.has_code}
                  >
                    Clear
                  </ha-button>
                </div>
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }

  render() {
    const lock = this._lock;
    return html`
      <ha-app-layout>
        <app-header slot="header" fixed>
          <app-toolbar class="topbar">
            <ha-menu-button .hass=${this.hass} .narrow=${this.isMobile}></ha-menu-button>
            <div class="title" main-title>🗝️ ZHA Lock Manager</div>
            <ha-button class="refresh" @click=${() => this._refresh()} ?disabled=${this._busy}>Refresh</ha-button>
          </app-toolbar>
        </app-header>

        <div class="wrap">
          ${this._error ? html`<div class="err">${this._error}</div>` : ""}
          <div class="cols ${this.isMobile ? "one" : ""}">
            <div class="left">
              <div class="card">
                <h3>Locks</h3>
                <ul class="list">
                  ${this._locks.map(
                    (l, idx) => html`
                      <li
                        class="${idx === this._selected ? "sel" : ""}"
                        @click=${() => {
                          this._selected = idx;
                          this.requestUpdate();
                        }}
                      >
                        <div class="name">${l.name}</div>
                        <div class="sub">${l.entity_id} · ${l.device_ieee}</div>
                      </li>
                    `
                  )}
                </ul>
              </div>
            </div>

            <div class="right">
              ${lock
                ? html`
                    <div class="card">
                      <h3>Lock: ${lock.name}</h3>
                      <div class="meta">
                        <label>Name <input id="name" .value=${lock.name} /></label>
                        <label>Max slots
                          <input id="max" type="number" min="1" max="250" .value=${String(lock.max_slots || 30)} />
                        </label>
                        <label>Slot offset <input id="offset" type="number" .value=${String(lock.slot_offset || 0)} /></label>
                        <ha-button class="save" @click=${() => this._saveMeta()} ?disabled=${this._busy}>Save</ha-button>
                      </div>
                    </div>

                    ${this.isMobile ? this._renderSlotsMobile(lock) : this._renderSlotsDesktop(lock)}
                  `
                : html`<div class="card">No locks configured in integration options.</div>`}
            </div>
          </div>
        </div>
      </ha-app-layout>
    `;
  }

  static get styles() {
    return css`
      :host { display: block; }

      /* Header */
      .topbar { padding: 0 8px; }
      .title { font-size: 24px; font-weight: 700; margin-left: 8px; }
      .refresh { margin-left: auto; } /* push to right */

      /* Layout */
      .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; }
      .cols { display: grid; grid-template-columns: 320px 1fr; gap: 16px; }
      .cols.one { grid-template-columns: 1fr; }
      .card { background: var(--card-background-color); border-radius: 16px; padding: 16px; box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,0.12)); margin-bottom: 10px; }
      h3 { margin: 0 0 12px; }

      /* Locks list */
      ul.list { list-style: none; margin: 0; padding: 0; }
      ul.list li { padding: 10px; border-radius: 12px; cursor: pointer; }
      ul.list li:hover { background: rgba(0,0,0,0.05); }
      ul.list li.sel { background: rgba(0,0,0,0.1); }
      .name { font-weight: 600; }
      .sub { font-size: 12px; opacity: 0.7; }

      /* Meta form, make Save align with inputs */
      .meta { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; align-items: center; }
      .meta label { display: inline-flex; flex-direction: column; }
      .meta input { height: 40px; padding: 6px 8px; }
      .meta .save { height: 40px; align-self: center; }

      /* Desktop table */
      table.slots { width: 100%; border-collapse: collapse; }
      table.slots th, table.slots td { padding: 8px; border-bottom: 1px solid rgba(0,0,0,0.08); }
      table.slots th { text-align: left; }
      table.slots th.col-actions, table.slots td.col-actions { text-align: center; }

      /* Equal width actions: three columns grid */
      .btn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
      .action { width: 100%; }

      /* Mobile stacked rows */
      .mobile-slots .mrow { padding: 10px 8px; border-bottom: 1px solid rgba(0,0,0,0.08); }
      .mobile-slots .mhead { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center; align-items: center; margin-bottom: 10px; }
      .mobile-slots .mcell { font-weight: 500; }
      .mobile-slots .mactions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }

      .err { background: #ffebee; color: #b71c1c; padding: 8px 12px; border-radius: 12px; margin-bottom: 8px; }

      /* Responsive tweaks */
      @media (max-width: 980px) {
        .meta { grid-template-columns: 1fr 1fr; }
      }
    `;
  }
}

customElements.define("zha-lock-manager-panel", ZhaLockManagerPanel);
export default ZhaLockManagerPanel;
