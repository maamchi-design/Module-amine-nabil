/** @odoo-module **/

/**
 * LoginWarningService - Client-Side Working Hours Monitor
 *
 * Purpose:
 *   This component acts as a real-time, client-side companion to the server-side
 *   working hours enforcement (ir_http.py). It monitors the current time in the
 *   user's browser and provides two key functions:
 *     1. A 5-minute warning notification before the user's working hours end.
 *     2. A forced page reload when working hours expire, which triggers the
 *        server-side logout via ir_http._dispatch().
 *
 * Execution Flow:
 *   1. setup()        → Initializes services (rpc, notification, user) from the
 *                        Owl environment. Calls startLogic().
 *   2. startLogic()   → Checks if the user is an admin (admins are exempt).
 *                        Fetches 'restrict_login_start_hour' and 'restrict_login_end_hour'
 *                        from the current company (res.company) via RPC.
 *                        Calls startCheckInterval() if valid hours are found.
 *   3. startCheckInterval() → Sets up two browser intervals:
 *                        - Every 1 minute: warning-only check (checkTime(true)).
 *                        - Every 5 minutes: full enforcement check (checkTime(false)).
 *                        Also runs an immediate check on load.
 *   4. checkTime()    → Converts the current browser time to Morocco timezone
 *                        (Africa/Casablanca). Compares against the company's end hour:
 *                        - If within 5 minutes of end: shows a sticky warning notification.
 *                        - If past end hour: triggers browser.location.reload(), which
 *                          causes ir_http._dispatch() to log the user out server-side.
 *
 * Related Models (Server-Side):
 *   - res.company: Reads 'restrict_login_start_hour' and 'restrict_login_end_hour'.
 *   - res.users: Admin group check via userService.hasGroup("base.group_system").
 *   - ir.http: Server-side enforcement that catches the reload and performs logout.
 *
 * Registration:
 *   Registered as a "main_component" in the Odoo web client registry, so it is
 *   automatically instantiated when the backend web client loads.
 */

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { Component, xml } from "@odoo/owl";

export class LoginWarningService extends Component {
    static template = xml`<div class="login_restriction_service" style="display:none;"/>`;

    setup() {
        try {
            this.rpc = this.env.services.rpc;
            this.notification = this.env.services.notification;
            this.userService = this.env.services.user;

            this.startLogic();
        } catch (error) {
            console.error("LoginWarningService failed to initialize gracefully:", error);
        }
    }

    async startLogic() {
        try {
            // Only non-admins need the warning
            const isAdmin = await this.userService.hasGroup("base.group_system");
            if (isAdmin) {
                return;
            }

            // Get current company ID safely
            const companyId = session.company_id || (session.user_companies && session.user_companies.current_company[0]);
            if (!companyId) {
                return;
            }

            // Fetch company hours from res.company
            const companyData = await this.rpc("/web/dataset/call_kw/res.company/read", {
                model: 'res.company',
                method: 'read',
                args: [[companyId], ['restrict_login_start_hour', 'restrict_login_end_hour']],
                kwargs: {},
            });

            if (companyData && companyData.length > 0) {
                this.startHour = companyData[0].restrict_login_start_hour;
                this.endHour = companyData[0].restrict_login_end_hour;
                this.startCheckInterval();
            }
        } catch (error) {
            console.error("Login Warning Service crashed but prevented white screen:", error);
        }
    }

    startCheckInterval() {
        // Check for 5-minute warning every 1 minute (for better UX)
        this.warningInterval = browser.setInterval(() => {
            this.checkTime(true); // warningOnly = true
        }, 60000);

        // Forced session validation every 5 minutes
        this.forceCheckInterval = browser.setInterval(() => {
            this.checkTime(false); // warningOnly = false (allow reload)
        }, 300000); // 5 minutes

        // Also check once immediately
        this.checkTime(false);
    }

    checkTime(warningOnly = false) {
        try {
            const now = new Date();
            // Convert to Morocco Time (Africa/Casablanca)
            const moroccoTimeStr = now.toLocaleString("en-US", { timeZone: "Africa/Casablanca", hour12: false });

            // Handle different locale string formats
            const timePart = moroccoTimeStr.includes(', ') ? moroccoTimeStr.split(', ')[1] : moroccoTimeStr.split(' ')[1];
            if (!timePart) return;

            const [h, m] = timePart.split(':').map(Number);
            const currentHour = h + m / 60.0;

            // 5 minutes before endHour
            const warningTime = this.endHour - (5 / 60.0);

            if (currentHour >= this.endHour) {
                if (!warningOnly) {
                    // Force logout by reloading (ir_http._dispatch will catch it and logout)
                    browser.location.reload();
                }
            } else if (currentHour >= warningTime && !this.warningShown) {
                this.notification.add(
                    "Warning: Working hours are ending soon. Please save your work.",
                    {
                        title: "Access Restriction",
                        type: "warning",
                        sticky: true,
                    }
                );
                this.warningShown = true;
            } else if (currentHour < warningTime) {
                this.warningShown = false;
            }
        } catch (e) {
            console.error("Login Warning check failed:", e);
        }
    }
}

// Register as a main component so it loads automatically with the web client
registry.category("main_components").add("LoginWarningService", {
    Component: LoginWarningService,
});
