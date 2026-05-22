"""
Visually designed email templates inspired by the GAB aesthetic references.
Each template uses fully inline CSS for email-client compatibility.
"""

DESIGNED_TEMPLATES = [

    # ── 1. The Ribbon ────────────────────────────────────────────────────────
    # Cream background, red wavy border, black bow at top — formal gift-like invite
    {
        "name": "The Ribbon",
        "type": "invite",
        "subject": "You're invited — {{ event_name }}",
        "body": """<div style="background:#f5f0e8;padding:0;margin:0;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">
    <tr>
      <td style="padding:0;">

        <!-- Bow SVG header -->
        <div style="text-align:center;padding:28px 40px 0;">
          <svg width="80" height="52" viewBox="0 0 80 52" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="22" cy="26" rx="18" ry="11" stroke="#c0392b" stroke-width="2.5" fill="none"/>
            <ellipse cx="58" cy="26" rx="18" ry="11" stroke="#c0392b" stroke-width="2.5" fill="none"/>
            <circle cx="40" cy="26" r="5" fill="#c0392b"/>
            <line x1="22" y1="26" x2="40" y2="26" stroke="#c0392b" stroke-width="2"/>
            <line x1="40" y1="26" x2="58" y2="26" stroke="#c0392b" stroke-width="2"/>
            <line x1="35" y1="31" x2="30" y2="46" stroke="#c0392b" stroke-width="2" stroke-linecap="round"/>
            <line x1="45" y1="31" x2="50" y2="46" stroke="#c0392b" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>

        <!-- Red border frame -->
        <div style="margin:16px 24px 24px;border:2.5px solid #c0392b;border-radius:2px;padding:32px 40px 36px;position:relative;">

          <!-- Corner ornaments -->
          <div style="position:absolute;top:-1px;left:-1px;width:16px;height:16px;border-top:4px solid #c0392b;border-left:4px solid #c0392b;"></div>
          <div style="position:absolute;top:-1px;right:-1px;width:16px;height:16px;border-top:4px solid #c0392b;border-right:4px solid #c0392b;"></div>
          <div style="position:absolute;bottom:-1px;left:-1px;width:16px;height:16px;border-bottom:4px solid #c0392b;border-left:4px solid #c0392b;"></div>
          <div style="position:absolute;bottom:-1px;right:-1px;width:16px;height:16px;border-bottom:4px solid #c0392b;border-right:4px solid #c0392b;"></div>

          <p style="margin:0 0 6px;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#9b8b7a;">GAB DINING CLUB</p>
          <p style="margin:0 0 20px;font-size:12px;color:#9b8b7a;">cordially invites</p>

          <p style="margin:0 0 4px;font-size:22px;font-style:italic;color:#2c2c2c;">Dear {{ name }},</p>

          <div style="width:40px;height:1px;background:#c0392b;margin:16px 0;"></div>

          <h1 style="margin:0 0 6px;font-size:28px;font-weight:normal;color:#1a1a1a;letter-spacing:0.04em;">{{ event_name }}</h1>

          <p style="margin:0 0 20px;font-size:14px;color:#5a4a3a;line-height:1.8;">{{ event_description }}</p>

          <table cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="padding-right:24px;">
                <p style="margin:0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#9b8b7a;">When</p>
                <p style="margin:4px 0 0;font-size:15px;color:#2c2c2c;font-style:italic;">{{ event_date }}</p>
              </td>
              <td style="border-left:1px solid #d4c4b4;padding-left:24px;">
                <p style="margin:0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#9b8b7a;">Where</p>
                <p style="margin:4px 0 0;font-size:15px;color:#2c2c2c;font-style:italic;">{{ event_location }}</p>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 6px;font-size:13px;color:#5a4a3a;line-height:1.7;">Please reply to let us know if you can join us. We hope to see you at the table.</p>

          <div style="width:40px;height:1px;background:#c0392b;margin:20px 0 16px;"></div>

          <p style="margin:0;font-size:12px;font-style:italic;color:#9b8b7a;">With love,<br>GAB Dining Club</p>
        </div>

      </td>
    </tr>
  </table>
</div>""",
    },

    # ── 2. Candlelight ───────────────────────────────────────────────────────
    # Dark leather texture, glowing string lights, warm amber gold — intimate dinner
    {
        "name": "Candlelight",
        "type": "invite",
        "subject": "An evening awaits — {{ event_name }}",
        "body": """<div style="background:#111008;margin:0;padding:0;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">
    <tr>
      <td>

        <!-- String lights header -->
        <div style="background:linear-gradient(180deg,#1a1408 0%,#111008 100%);padding:32px 40px 24px;text-align:center;position:relative;overflow:hidden;">

          <!-- Simulated string lights using circles -->
          <div style="position:relative;height:48px;margin-bottom:8px;">
            <div style="position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#b8960040,#c8a800,#b8960040,transparent);top:12px;"></div>
            <!-- Light bulbs -->
            <span style="position:absolute;left:10%;top:8px;font-size:18px;filter:drop-shadow(0 0 8px #ffcc44);">💡</span>
            <span style="position:absolute;left:28%;top:4px;font-size:16px;filter:drop-shadow(0 0 8px #ffcc44);">💡</span>
            <span style="position:absolute;left:50%;top:6px;font-size:18px;filter:drop-shadow(0 0 8px #ffcc44);">💡</span>
            <span style="position:absolute;left:70%;top:3px;font-size:16px;filter:drop-shadow(0 0 8px #ffcc44);">💡</span>
            <span style="position:absolute;right:8%;top:8px;font-size:18px;filter:drop-shadow(0 0 8px #ffcc44);">💡</span>
          </div>

          <p style="margin:16px 0 4px;font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:#8a7a5a;">GAB DINING CLUB</p>
          <p style="margin:0;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">presents</p>
        </div>

        <!-- Main content -->
        <div style="padding:8px 48px 40px;background:#111008;">

          <h1 style="margin:0 0 8px;font-size:34px;font-weight:normal;color:#d4aa4a;letter-spacing:0.06em;text-align:center;">{{ event_name }}</h1>
          <div style="text-align:center;margin-bottom:28px;">
            <div style="display:inline-block;width:48px;height:1px;background:#3a3020;vertical-align:middle;"></div>
            <span style="color:#5a4e38;font-size:14px;padding:0 12px;">✦</span>
            <div style="display:inline-block;width:48px;height:1px;background:#3a3020;vertical-align:middle;"></div>
          </div>

          <p style="margin:0 0 20px;font-size:16px;color:#c8b870;font-style:italic;text-align:center;">Dear {{ name }},</p>

          <p style="margin:0 0 20px;font-size:14px;color:#a09070;line-height:1.85;text-align:center;">{{ event_description }}</p>

          <!-- Details block -->
          <div style="border:1px solid #2e2818;padding:20px 24px;margin:24px 0;text-align:center;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:8px 16px;border-right:1px solid #2e2818;text-align:center;">
                  <p style="margin:0;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">When</p>
                  <p style="margin:6px 0 0;font-size:15px;color:#c8b870;font-style:italic;">{{ event_date }}</p>
                </td>
                <td style="padding:8px 16px;text-align:center;">
                  <p style="margin:0;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#5a4e38;">Where</p>
                  <p style="margin:6px 0 0;font-size:15px;color:#c8b870;font-style:italic;">{{ event_location }}</p>
                </td>
              </tr>
            </table>
          </div>

          <p style="margin:20px 0 0;font-size:13px;color:#5a4e38;text-align:center;line-height:1.8;">Reply to this email to confirm your seat.</p>
          <p style="margin:24px 0 0;font-size:12px;font-style:italic;color:#3a3020;text-align:center;">With love,<br><span style="color:#8a7a5a;letter-spacing:0.08em;">GAB DINING CLUB</span></p>
        </div>

      </td>
    </tr>
  </table>
</div>""",
    },

    # ── 3. Mediterranean Table ────────────────────────────────────────────────
    # Watercolor lemon/olive border, checkered warmth, Italian bistro feel
    {
        "name": "Mediterranean Table",
        "type": "invite",
        "subject": "Join us at the table — {{ event_name }}",
        "body": """<div style="background:#fffdf8;margin:0;padding:0;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;margin:0 auto;border:2px solid #c0583a;">
    <tr>
      <td>

        <!-- Top botanical header -->
        <div style="background:#fffdf8;padding:24px 40px 16px;text-align:center;border-bottom:1px solid #f0e0d0;">
          <!-- Lemon/leaf motif using emoji and styled text -->
          <div style="font-size:22px;letter-spacing:6px;margin-bottom:8px;">🍋 🫒 🌿 🫒 🍋</div>
          <div style="width:100%;height:1px;background:linear-gradient(90deg,transparent,#c0583a,transparent);margin:8px 0;"></div>
        </div>

        <!-- Main body -->
        <div style="padding:28px 48px;background:#fffdf8;">

          <p style="margin:0 0 4px;font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:#9b6a4a;text-align:center;">GAB DINING CLUB</p>
          <h1 style="margin:8px 0 4px;font-size:30px;font-weight:normal;color:#1a1a1a;text-align:center;letter-spacing:0.02em;">{{ event_name }}</h1>

          <div style="text-align:center;margin:12px 0 20px;">
            <span style="color:#c0583a;font-size:18px;">— ✦ —</span>
          </div>

          <p style="margin:0 0 18px;font-size:15px;color:#3a2a1a;font-style:italic;text-align:center;">Caro/Cara {{ name }},</p>

          <p style="margin:0 0 20px;font-size:14px;color:#5a4030;line-height:1.9;text-align:center;">{{ event_description }}</p>

          <!-- Checkered detail divider -->
          <div style="text-align:center;margin:20px 0;">
            <div style="display:inline-block;background:repeating-linear-gradient(45deg,#c0583a 0,#c0583a 4px,transparent 0,transparent 50%) 0/8px 8px;width:80px;height:8px;opacity:0.4;"></div>
          </div>

          <!-- Details -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="width:50%;padding:12px 16px 12px 0;border-right:1px solid #e8d8c8;text-align:right;vertical-align:top;">
                <p style="margin:0;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:#9b6a4a;">When</p>
                <p style="margin:4px 0 0;font-size:14px;color:#2c2c2c;font-style:italic;">{{ event_date }}</p>
              </td>
              <td style="width:50%;padding:12px 0 12px 16px;text-align:left;vertical-align:top;">
                <p style="margin:0;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:#9b6a4a;">Where</p>
                <p style="margin:4px 0 0;font-size:14px;color:#2c2c2c;font-style:italic;">{{ event_location }}</p>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 20px;font-size:13px;color:#7a5a40;text-align:center;line-height:1.7;">Do let us know if you'll be joining — we'll save your seat.</p>
        </div>

        <!-- Bottom footer with checkered border feel -->
        <div style="background:#c0583a;padding:14px 40px;text-align:center;">
          <p style="margin:0;font-size:11px;letter-spacing:0.16em;color:#fff3ee;text-transform:uppercase;">With love · GAB Dining Club</p>
        </div>

      </td>
    </tr>
  </table>
</div>""",
    },

    # ── 4. Red Velvet ────────────────────────────────────────────────────────
    # Deep crimson background, gold stars, disco energy, glamorous night out
    {
        "name": "Red Velvet",
        "type": "invite",
        "subject": "✦ {{ event_name }} — an evening you won't forget",
        "body": """<div style="background:#7a0e18;margin:0;padding:0;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:linear-gradient(160deg,#8a1420 0%,#6a0c14 50%,#5a0a10 100%);">
    <tr>
      <td style="padding:40px 48px;">

        <!-- Top scattered stars -->
        <div style="text-align:center;margin-bottom:8px;">
          <span style="color:#d4aa4a;font-size:12px;letter-spacing:16px;">✦ ✦ ✦ ✦ ✦</span>
        </div>

        <!-- Torn paper effect top accent -->
        <div style="background:#f5f0e4;margin:-8px -16px 28px;padding:10px 28px;position:relative;transform:rotate(-0.5deg);">
          <p style="margin:0;font-size:10px;letter-spacing:0.22em;text-transform:uppercase;color:#7a0e18;font-family:Georgia,serif;">GAB DINING CLUB ✦ AN INTIMATE EVENING</p>
        </div>

        <h1 style="margin:0 0 6px;font-size:38px;font-weight:normal;color:#f0d870;letter-spacing:0.04em;text-shadow:0 2px 12px rgba(0,0,0,0.4);">{{ event_name }}</h1>

        <div style="margin:16px 0 24px;">
          <span style="color:#d4aa4a;font-size:20px;letter-spacing:8px;">✦ ✦ ✦</span>
        </div>

        <p style="margin:0 0 18px;font-size:17px;color:#f0d870;font-style:italic;">Dearest {{ name }},</p>

        <p style="margin:0 0 24px;font-size:14px;color:#e8c090;line-height:1.9;">{{ event_description }}</p>

        <!-- Details in styled boxes -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
          <tr>
            <td style="width:48%;background:rgba(0,0,0,0.25);border:1px solid #9a1828;padding:14px 16px;border-radius:2px;">
              <p style="margin:0;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#c8984a;">When</p>
              <p style="margin:6px 0 0;font-size:15px;color:#f0d870;font-style:italic;">{{ event_date }}</p>
            </td>
            <td style="width:4%;"></td>
            <td style="width:48%;background:rgba(0,0,0,0.25);border:1px solid #9a1828;padding:14px 16px;border-radius:2px;">
              <p style="margin:0;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#c8984a;">Where</p>
              <p style="margin:6px 0 0;font-size:15px;color:#f0d870;font-style:italic;">{{ event_location }}</p>
            </td>
          </tr>
        </table>

        <!-- Champagne icon -->
        <div style="text-align:center;margin:0 0 20px;font-size:24px;">🥂</div>

        <p style="margin:0 0 8px;font-size:13px;color:#c8904a;text-align:center;">Reply to confirm — seats are limited.</p>

        <!-- Bottom stars -->
        <div style="text-align:center;margin-top:28px;">
          <span style="color:#d4aa4a;font-size:12px;letter-spacing:20px;">✦ ✦ ✦ ✦</span>
        </div>
        <p style="margin:16px 0 0;font-size:11px;font-style:italic;color:#8a4a30;text-align:center;letter-spacing:0.1em;">WITH LOVE · GAB DINING CLUB</p>

      </td>
    </tr>
  </table>
</div>""",
    },

    # ── 5. The Menu Card ─────────────────────────────────────────────────────
    # Dark brown/near-black, gold ornate script, formal tasting menu announcement
    {
        "name": "The Menu Card",
        "type": "invite",
        "subject": "{{ event_name }} — the menu awaits",
        "body": """<div style="background:#1a1008;margin:0;padding:0;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;margin:0 auto;background:linear-gradient(180deg,#1e1408 0%,#120d04 100%);">
    <tr>
      <td style="padding:0;">

        <!-- Ornate gold border frame -->
        <div style="margin:24px;border:1px solid #7a6020;padding:40px 44px;position:relative;">

          <!-- Corner flourishes -->
          <div style="position:absolute;top:6px;left:6px;font-size:20px;color:#7a6020;line-height:1;">❧</div>
          <div style="position:absolute;top:6px;right:6px;font-size:20px;color:#7a6020;line-height:1;transform:scaleX(-1);">❧</div>
          <div style="position:absolute;bottom:6px;left:6px;font-size:20px;color:#7a6020;line-height:1;transform:scaleY(-1);">❧</div>
          <div style="position:absolute;bottom:6px;right:6px;font-size:20px;color:#7a6020;line-height:1;transform:scale(-1);">❧</div>

          <!-- Top ornament -->
          <div style="text-align:center;margin-bottom:20px;">
            <span style="color:#8a7030;font-size:13px;letter-spacing:8px;">— ✦ ✦ ✦ —</span>
          </div>

          <p style="margin:0 0 4px;font-size:9px;letter-spacing:0.28em;text-transform:uppercase;color:#6a5820;text-align:center;">GAB DINING CLUB</p>
          <p style="margin:0 0 20px;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#4a3e18;text-align:center;">cordially presents</p>

          <h1 style="margin:0 0 8px;font-size:32px;font-weight:normal;color:#c8a840;text-align:center;font-style:italic;letter-spacing:0.04em;">{{ event_name }}</h1>

          <div style="text-align:center;margin:16px 0;">
            <div style="display:inline-block;width:60px;height:1px;background:#4a3e18;vertical-align:middle;"></div>
            <span style="color:#7a6020;font-size:16px;padding:0 10px;">✦</span>
            <div style="display:inline-block;width:60px;height:1px;background:#4a3e18;vertical-align:middle;"></div>
          </div>

          <p style="margin:0 0 24px;font-size:14px;color:#a08040;font-style:italic;text-align:center;">Dear {{ name }},</p>

          <p style="margin:0 0 24px;font-size:13px;color:#7a6830;line-height:1.95;text-align:center;">{{ event_description }}</p>

          <!-- Details in gold rule boxes -->
          <div style="border-top:1px solid #3a3010;border-bottom:1px solid #3a3010;padding:16px 0;margin-bottom:24px;text-align:center;">
            <p style="margin:0 0 4px;font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:#5a4e20;">When &amp; Where</p>
            <p style="margin:0;font-size:15px;color:#c8a840;font-style:italic;">{{ event_date }}</p>
            <p style="margin:4px 0 0;font-size:14px;color:#8a7830;font-style:italic;">{{ event_location }}</p>
          </div>

          <p style="margin:0 0 0;font-size:12px;color:#5a4e20;text-align:center;line-height:1.8;">Kindly reply at your earliest convenience.<br>We look forward to welcoming you.</p>

          <!-- Bottom ornament -->
          <div style="text-align:center;margin-top:24px;">
            <span style="color:#8a7030;font-size:13px;letter-spacing:8px;">— ✦ ✦ ✦ —</span>
          </div>

          <p style="margin:16px 0 0;font-size:10px;letter-spacing:0.16em;text-transform:uppercase;color:#4a3e18;text-align:center;font-style:italic;">With love · GAB Dining Club</p>
        </div>

      </td>
    </tr>
  </table>
</div>""",
    },

    # ── 6. The Arch ──────────────────────────────────────────────────────────
    # Cream/blush, thin red arch line, sparkle stars, illustrated cocktail cocktail vibe
    {
        "name": "The Arch",
        "type": "invite",
        "subject": "{{ event_name }} — you're invited ✦",
        "body": """<div style="background:#fdf5f0;margin:0;padding:0;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;">
    <tr>
      <td style="padding:32px 40px 40px;">

        <!-- Scattered sparkles top -->
        <div style="text-align:center;margin-bottom:4px;">
          <span style="color:#d45a4a;font-size:14px;letter-spacing:24px;">✦ ✦ ✦</span>
        </div>

        <!-- SVG arch -->
        <div style="text-align:center;margin-bottom:0;">
          <svg width="340" height="200" viewBox="0 0 340 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Arch outline -->
            <path d="M40 200 L40 100 Q40 20 170 20 Q300 20 300 100 L300 200" stroke="#d45a4a" stroke-width="1.5" fill="none"/>
            <!-- Inner arch -->
            <rect x="20" y="195" width="300" height="1" fill="#d45a4a" opacity="0.3"/>

            <!-- Content inside arch -->
            <text x="170" y="68" text-anchor="middle" font-family="Georgia,serif" font-size="9" fill="#9a5040" letter-spacing="3">GAB DINING CLUB</text>
            <text x="170" y="96" text-anchor="middle" font-family="Georgia,serif" font-size="20" fill="#1a1a1a" font-style="italic">{{ event_name }}</text>
            <line x1="110" y1="108" x2="230" y2="108" stroke="#d45a4a" stroke-width="0.8" opacity="0.5"/>
            <text x="170" y="128" text-anchor="middle" font-family="Georgia,serif" font-size="11" fill="#7a4a3a">{{ event_date }}</text>
            <text x="170" y="148" text-anchor="middle" font-family="Georgia,serif" font-size="11" fill="#9a6050">{{ event_location }}</text>

            <!-- Corner sparkles -->
            <text x="28" y="32" font-size="10" fill="#d45a4a">✦</text>
            <text x="302" y="32" font-size="10" fill="#d45a4a">✦</text>
            <text x="12" y="185" font-size="8" fill="#d45a4a">✦</text>
            <text x="316" y="185" font-size="8" fill="#d45a4a">✦</text>
          </svg>
        </div>

        <!-- Body text below arch -->
        <div style="text-align:center;margin-top:16px;">
          <p style="margin:0 0 14px;font-size:16px;color:#3a2820;font-style:italic;">Dear {{ name }},</p>
          <p style="margin:0 0 20px;font-size:13px;color:#7a5848;line-height:1.85;">{{ event_description }}</p>

          <div style="margin:0 auto 20px;width:48px;height:1px;background:#d45a4a;opacity:0.5;"></div>

          <p style="margin:0 0 24px;font-size:12px;color:#9a7060;">Please reply to confirm your seat at the table.</p>

          <div style="margin-bottom:4px;font-size:10px;letter-spacing:16px;color:#d45a4a;">✦ ✦ ✦</div>
          <p style="margin:12px 0 0;font-size:11px;font-style:italic;color:#c09080;letter-spacing:0.06em;">With love · GAB Dining Club</p>
        </div>

      </td>
    </tr>
  </table>
</div>""",
    },

]
