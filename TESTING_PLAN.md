# TraceIQ Testing Plan

This document outlines the systematic testing strategy for the TraceIQ application. Each feature will be tested manually and/or automatically to ensure functionality and stability.

## 🟢 1. Authentication & Session Management
- [ ] **Login with valid credentials**
  - **Input:** `admin` / `admin123`
  - **Expected:** Redirect to Dashboard, JWT token stored in localStorage/cookies.
- [ ] **Login with invalid credentials**
  - **Input:** `admin` / `wrongpass`
  - **Expected:** Error message "Invalid credentials", stay on login page.
- [ ] **Access protected route without login**
  - **Action:** Navigate to `/dashboard` directly in private window.
  - **Expected:** Redirect to `/login`.
- [ ] **Logout**
  - **Action:** Click "Logout" in user menu.
  - **Expected:** Redirect to `/login`, token cleared.

## 🟢 2. Dashboard & Navigation
- [ ] **Dashboard Loading**
  - **Action:** Load `/dashboard`.
  - **Expected:** Render sidebar, stats cards, recent activity without crashing.
- [ ] **Sidebar Navigation**
  - **Action:** Click "Criminals", "Cases", "Users".
  - **Expected:** URL changes, correct active state in sidebar, page content renders.
- [ ] **User Profile Menu**
  - **Action:** Click user avatar.
  - **Expected:** Dropdown appears with "Profile", "Settings", "Logout".

## 🟡 3. User Management (Admin Only)
- [ ] **List Users**
  - **Action:** Navigate to `/users`.
  - **Expected:** Table displays list of users (at least `admin` should be there).
- [ ] **Create User**
  - **Action:** Click "Add User", fill form (Officer Name, Role: Field Officer).
  - **Expected:** User created, appears in list.
- [ ] **Edit User**
  - **Action:** Change role or status of created user.
  - **Expected:** Updates reflected.

## 🟡 4. Criminal Record Management (Core Functionality)
- [ ] **List Criminals**
  - **Action:** Navigate to `/criminals`.
  - **Expected:** Table displays criminals (empty initially).
- [ ] **Create Criminal Profile**
  - **Action:** Click "New Profile", fill mandatory fields (Name, NIC, Gender).
  - **Expected:** Profile created, redirected to detail view.
- [ ] **Search Criminals**
  - **Action:** Type name/NIC in search bar.
  - **Expected:** filtered results.
- [ ] **View Profile (Dossier)**
  - **Action:** Click on a criminal.
  - **Expected:** Detailed view showing info, offenses, mugshots.

## 🟡 5. Case Management
- [ ] **List Cases**
  - **Action:** Navigate to `/cases`.
  - **Expected:** List of active cases.
- [ ] **Create Case**
  - **Action:** Create new case, assign lead officer.
  - **Expected:** Case created.

## 🔴 6. AI & Face Recognition (Known Issues)
- [ ] **Face Embedding Generation**
  - **Current Status:** **BLOCKED** (pgvector missing).
  - **Test:** Verify app handles this gracefully (e.g., specific error message or disabled feature) rather than crashing the whole backend.

---

## Testing Log

| Date | Feature | Status | Notes |
|------|---------|--------|-------|
| 2026-02-12 | Auth | Pending | |
