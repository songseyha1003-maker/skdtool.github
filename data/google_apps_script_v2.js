// =========================================================================
//  SN TOOL PRO - ENTERPRISE CLOUD TELEMETRY & SYNC ENGINE (v2.0)
//  Self-Healing Headers, Bidirectional Sync, Auto-Formatting & Realtime Tracker
// =========================================================================

function doGet(e) {
  var action = (e && e.parameter && e.parameter.action) ? e.parameter.action : "get_all";
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  if (action === "ping") {
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      status: "online",
      version: "2.0.0",
      sheet_name: sheet.getName(),
      total_rows: sheet.getLastRow(),
      timestamp: new Date()
    })).setMimeType(ContentService.MimeType.JSON);
  }
  
  if (action === "get_all") {
    var data = sheet.getDataRange().getValues();
    var heartbeats = {};
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      var key = String(row[0] || "").trim().toUpperCase();
      if (key && key !== "LICENSE KEY") {
        var dateVal = row[2];
        var formattedDate = dateVal;
        if (dateVal instanceof Date) {
          formattedDate = Utilities.formatDate(dateVal, "GMT+7", "yyyy-MM-dd HH:mm:ss");
        }
        heartbeats[key] = {
          license_key: key,
          client_name: String(row[1] || ""),
          last_active: String(formattedDate || "Never"),
          use_count: Number(row[3]) || 0,
          hwid: String(row[4] || "")
        };
      }
    }
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      count: Object.keys(heartbeats).length,
      heartbeats: heartbeats
    })).setMimeType(ContentService.MimeType.JSON);
  }
  
  return ContentService.createTextOutput(JSON.stringify({ success: true, status: "ready" }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    var contents = e.postData.contents;
    var postData = JSON.parse(contents);
    var action = postData.action || "heartbeat";
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var nowFormatted = Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd HH:mm:ss");

    // =====================================================================
    // 1. ACTION: SYNC_ALL / CLEAN_RESET (Mass Sync & Beautiful Auto-Formatting)
    // =====================================================================
    if (action === "sync_all" || action === "clean_reset") {
      var customers = postData.customers || [];
      sheet.clear();
      
      // Setup Beautiful Dark Header
      var headers = [["License Key", "Client Name", "Last Active", "Use Count", "HWID", "Plan", "Status"]];
      var headerRange = sheet.getRange(1, 1, 1, 7);
      headerRange.setValues(headers)
        .setFontWeight("bold")
        .setFontSize(11)
        .setBackground("#0f172a")
        .setFontColor("#f8fafc")
        .setHorizontalAlignment("center")
        .setVerticalAlignment("middle");
      
      sheet.setFrozenRows(1);
      sheet.setRowHeight(1, 38);

      if (customers.length > 0) {
        var rows = [];
        for (var i = 0; i < customers.length; i++) {
          var c = customers[i];
          rows.push([
            String(c.license_key || "").toUpperCase(),
            String(c.client_name || "Customer"),
            String(c.last_active || "Never"),
            Number(c.use_count) || 0,
            String(c.bound_hwid || c.hwid || "ANY"),
            String(c.plan || "PRO"),
            String(c.status || "ACTIVE")
          ]);
        }
        var dataRange = sheet.getRange(2, 1, rows.length, 7);
        dataRange.setValues(rows).setVerticalAlignment("middle");
        
        // Alignment formatting
        sheet.getRange(2, 3, rows.length, 1).setHorizontalAlignment("center");
        sheet.getRange(2, 4, rows.length, 1).setHorizontalAlignment("center").setFontWeight("bold");
        sheet.getRange(2, 6, rows.length, 2).setHorizontalAlignment("center");
        
        // Zebra striping
        for (var r = 0; r < rows.length; r++) {
          sheet.setRowHeight(r + 2, 30);
          if (r % 2 === 1) {
            sheet.getRange(r + 2, 1, 1, 7).setBackground("#f8fafc");
          }
        }
      }
      sheet.autoResizeColumns(1, 7);
      return ContentService.createTextOutput(JSON.stringify({
        success: true,
        message: "Sheet completely synchronized and formatted!",
        synced_count: customers.length
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // =====================================================================
    // 2. ACTION: DELETE (Remove key when deleted on Admin Dashboard)
    // =====================================================================
    if (action === "delete") {
      var delKey = String(postData.license_key || "").trim().toUpperCase();
      var data = sheet.getDataRange().getValues();
      for (var i = 1; i < data.length; i++) {
        if (String(data[i][0]).trim().toUpperCase() === delKey) {
          sheet.deleteRow(i + 1);
          return ContentService.createTextOutput(JSON.stringify({ success: true, deleted: delKey }))
            .setMimeType(ContentService.MimeType.JSON);
        }
      }
      return ContentService.createTextOutput(JSON.stringify({ success: true, not_found: true }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // =====================================================================
    // 3. ACTION: HEARTBEAT (Client App Automatic Telemetry Ping)
    // =====================================================================
    var key = String(postData.license_key || "").trim().toUpperCase();
    var hwid = String(postData.hwid || "").trim();
    var clientName = String(postData.client_name || "").trim();
    
    if (!key) {
      return ContentService.createTextOutput(JSON.stringify({ success: false, error: "No license_key" }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Self-heal header if missing or damaged
    var data = sheet.getDataRange().getValues();
    if (data.length === 0 || String(data[0][0]).trim().toUpperCase() !== "LICENSE KEY") {
      sheet.insertRowsBefore(1, 1);
      sheet.getRange(1, 1, 1, 7).setValues([["License Key", "Client Name", "Last Active", "Use Count", "HWID", "Plan", "Status"]])
        .setFontWeight("bold").setBackground("#0f172a").setFontColor("#f8fafc").setHorizontalAlignment("center");
      sheet.setFrozenRows(1);
      sheet.setRowHeight(1, 38);
      data = sheet.getDataRange().getValues();
    }
    
    var foundRow = -1;
    for (var i = 1; i < data.length; i++) {
      if (String(data[i][0]).trim().toUpperCase() === key) {
        foundRow = i + 1;
        break;
      }
    }
    
    if (foundRow > 0) {
      var currentCount = Number(sheet.getRange(foundRow, 4).getValue()) || 0;
      sheet.getRange(foundRow, 3).setValue(nowFormatted);
      sheet.getRange(foundRow, 4).setValue(currentCount + 1);
      if (hwid && (!sheet.getRange(foundRow, 5).getValue() || sheet.getRange(foundRow, 5).getValue() === "ANY")) {
        sheet.getRange(foundRow, 5).setValue(hwid);
      }
      if (clientName && (!sheet.getRange(foundRow, 2).getValue() || sheet.getRange(foundRow, 2).getValue() === "User")) {
        sheet.getRange(foundRow, 2).setValue(clientName);
      }
    } else {
      sheet.appendRow([key, clientName || "User", nowFormatted, 1, hwid || "ANY", "PRO", "ACTIVE"]);
      var lastR = sheet.getLastRow();
      sheet.setRowHeight(lastR, 30);
      sheet.getRange(lastR, 4).setHorizontalAlignment("center").setFontWeight("bold");
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      last_active: nowFormatted,
      license_key: key
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ success: false, error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

