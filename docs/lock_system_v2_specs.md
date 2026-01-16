# LBS Lock System Specification (V2.1) CRUD Summary

**判定の基本原則 (Child Priority)**
Agentの操作可否は、「Exceptionが存在すればそのLock状態、なければTaskのLock状態」によって決定されます。

### 1. Behavior Matrix (Agent Permissions)

| Case | Task Lock | Exception State | **Agent Permission** | 意味・ユースケース |
| :--- | :---: | :---: | :---: | :--- |
| **1** | 🔒 **ON** | **None** | ⛔ **DENY** | **Global Freeze** (固定バイト等) |
| **2** | 🔒 **ON** | 🔒 **Locked** | ⛔ **DENY** | **Reinforced Lock** (厳重固定) |
| **3** | 🔒 **ON** | 🔓 **Unlocked** | ✅ **ALLOW** | **Specific Day Release** (特定日解放) |
| **4** | 🔓 **OFF** | **None** | ✅ **ALLOW** | **Standard** (通常タスク) |
| **5** | 🔓 **OFF** | 🔒 **Locked** | ⛔ **DENY** | **Local Pinning** (特定日固定/試験日等) |
| **6** | 🔓 **OFF** | 🔓 **Unlocked** | ✅ **ALLOW** | **Redundant Open** (自由) |

### 2. CRUD Operations Detail

**A. Task Operations (定義変更)**
Exceptionの状態に関わらず、Task自身のLock状態のみで判定します。

*   **Task Locked:** Readのみ可。Update/Deleteは不可。
*   **Task Unlocked:** 全操作可。

**B. Exception Operations (スケジュール変更)**
上記のMatrixに基づき判定します。

| Action | Case 1, 2, 5 (Locked) | Case 3, 4, 6 (Allowed) |
| :--- | :--- | :--- |
| **Create** (新規例外作成) | ⛔ **Block** | ✅ **Allow** |
| **Update** (既存例外変更) | ⛔ **Block** | ✅ **Allow** |
| **Delete** (例外削除/デフォルト戻し) | ⛔ **Block** | ✅ **Allow** (*Case 3含む) |

**C. Execution Operations (実績記録)**
Lock状態に関わらず、常に許可されます。

*   **Update Status (Done/Todo):** ✅ **Always Allowed**
