# Aspire Cloud Knowledge Base

**Landscape and Maintenance Management System**  
**URL:** https://cloud.youraspire.com/

---

## 📚 Main Modules

### 1. [Work Tickets (Invoices)](./invoices-module.md)
Managing individual work orders - the representation of a job or task your company performs for a customer.

**Use cases:**
- Review work ticket statuses (Open, Scheduled, Complete, Pending Approval, Cancelled)
- Complete or cancel tickets in bulk
- Understand the work ticket lifecycle
- Use Dynamic Forecasting for financial planning

### 2. [Opportunities](./opportunities-module.md)
Managing contracts and work orders - the sales pipeline and project estimation.

**Use cases:**
- Create opportunities (Contracts vs Work Orders)
- Build estimates for customers
- Choose the correct billing type (Fixed Payment, Per Service, T&M, etc.)
- Win, lose, or cancel opportunities
- Make changes to active contracts

---

## 🔍 Quick Reference Guide

### If the user asks about...

| Topic | See module |
|------|-----------|
| "How do I mark a job as complete?" | [Work Tickets](./invoices-module.md) |
| "What is a work ticket?" | [Work Tickets](./invoices-module.md) |
| "How do I cancel tickets?" | [Work Tickets](./invoices-module.md) |
| "What is Dynamic Forecasting?" | [Work Tickets](./invoices-module.md) |
| "How do I create a contract?" | [Opportunities](./opportunities-module.md) |
| "What billing type should I use?" | [Opportunities](./opportunities-module.md) |
| "How do I create an estimate?" | [Opportunities](./opportunities-module.md) |
| "What is Fixed Payment?" | [Opportunities](./opportunities-module.md) |
| "How do multi-year contracts work?" | [Opportunities](./opportunities-module.md) |
| "What is a change order?" | [Opportunities](./opportunities-module.md) |

---

## 📖 Key Aspire Concepts

### System Hierarchy
```
Property (Customer location)
  └── Opportunity (Contract or Work Order)
       └── Estimate (Proposal)
            └── Services
                 └── Items (Labor, materials, equipment)
                      └── Work Tickets (Generated work orders)
```

### Opportunity Types
- **Contract:** Recurring work (maintenance, snow)
- **Work Order:** One-time jobs (installation, construction)

### Invoice Types

**For Contracts:**
- **Fixed Payment:** Fixed monthly payment
- **Per Service:** Bill per completed event
- **T&M (Time & Materials):** Bill for actual time and materials

**For Work Orders:**
- **Fixed Price on Completion:** One invoice when everything is done
- **Fixed Price on Payment Schedule:** Payments by milestone
- **T&M on Completion:** Bill time/materials at the end
- **Fixed Price Open Billing:** Bill any amount at any time

---

## ⚠️ Important System Rules

1. **Aspire is Property-centric:** Everything is created from the customer's property, not directly from modules
2. **One Opportunity = One Contract:** Each new project needs its own opportunity
3. **Work Tickets are auto-generated** when you win an opportunity
4. **Won changes cannot be undone:** Be very careful when marking as Won
5. **Closed months cannot be edited:** Tickets can only be completed/approved in open months

---

## 🎯 Typical Workflow

```
1. Customer contacts → 2. Create Property → 3. Create Opportunity → 
4. Build Estimate → 5. Send Proposal → 6. Customer accepts → 
7. Mark Won → 8. Work Tickets created → 9. Schedule work → 
10. Complete tickets → 11. Invoice
```

---

## 🔗 Additional Resources

- **Official documentation:** https://guide.youraspire.com/
- **System:** https://cloud.youraspire.com/

---

**Last updated:** April 2026  
**Modules covered:** Work Tickets (Invoices), Opportunities
