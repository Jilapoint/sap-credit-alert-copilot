# SAP Credit Alert in Teams with Copilot Studio

A Copilot Studio agent that checks SAP credit data every working day at 07:30, finds the customers
over their credit limit or more than 30 days overdue, qualifies each one (likely cause, priority,
recommended action) and posts a brief in a Teams channel. After the brief, the same agent answers
the team's follow-up questions in the channel.

Tested without an S/4HANA: the SAP side is a small mock service on SAP BTP that serves generated
credit data with the same field names a real S/4HANA OData API would return.

## What is in this repository

| Item | What it is |
|---|---|
| `SAPCreditAlertCopilot_1_0_0_1.zip` | Power Platform solution: the Copilot Studio agent **SAP Credit Alert**, its agent flow **Post credit alert to Teams**, connection references |
| `insightflow/` | The SAP mock: an SAP CAP (Node.js) project that serves three read-only OData v4 entities from CSV files — `A_BusinessPartner`, `CreditManagementAccount`, `CustomerOpenItem` |

## How it works

1. A scheduled trigger in Copilot Studio wakes the agent at 07:30 (Monday to Friday).
2. The agent calls SAP through the SAP OData connector: credit accounts, open items, customer names.
3. It keeps customers where `IsCreditLimitExceeded = true` or `MaxDaysOverdue > 30`, then for each one sets a likely cause, a priority (amount × days × risk class) and one recommended action.
4. An agent flow builds an adaptive card and posts it in the **Credit and Collections** channel.
5. In the channel, analysts ask `@SAP Credit Alert why is Northwind blocked?` or `draft the reminder for Contoso`. The agent answers from the same SAP data and drafts emails without sending them.

The agent never writes to SAP. Blocking a delivery or changing a limit stays a human decision in SAP.

## Deploy the mock (SAP side)

```bash
cd insightflow
npm install
npm run watch        # local test: http://localhost:4004/odata/v4/credit/CreditManagementAccount?$filter=IsCreditLimitExceeded eq true
cds build --production
cf login -a https://api.cf.<region>.hana.ondemand.com
cf push              # note the route: https://<route>/odata/v4/credit is the base URL for the connector
```

Expected test result: 3 customers (1000101, 1000102, 1000103). The data set holds 10 customers and
28 open invoices; 5 customers are designed to trigger the alert.

## Import the solution (Microsoft side)

1. [make.powerapps.com](https://make.powerapps.com) → **Solutions** → **Import solution** → choose the zip.
2. Map the two connections when asked: **SAP OData** (base URL of the mock, no authentication) and **Microsoft Teams** (your account).
3. After import, open the agent in Copilot Studio → check the three tools point to your mock URL → **Publish**.
4. Open the flow **Post credit alert to Teams** → set your team and channel → turn it on.
5. Test in the Copilot Studio test pane with: `Run the daily credit check and post the alert to Teams.`

Prerequisites: Copilot Studio capacity allocated to the environment (needed by agent flows and the
scheduled trigger), and a DLP policy that keeps SAP OData and Microsoft Teams in the same data group.

## Pitfalls met on the way

- The SAP OData connector encodes `$filter` spaces as `+`; the mock rewrites them to `%20` in `server.js`.
- The connector rejects `Edm.Date` values from CAP, so dates are declared as strings in the mock.
