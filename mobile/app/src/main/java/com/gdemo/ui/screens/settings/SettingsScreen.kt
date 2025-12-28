package com.gdemo.ui.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.HorizontalDivider
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.gdemo.BuildConfig
import com.gdemo.data.local.ConnectionSettings
import com.gdemo.data.local.loadConnection
import com.gdemo.data.local.saveConnection
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.remote.ApiService
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(paddingValues: PaddingValues) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    var baseUrl by rememberSaveable { mutableStateOf(stored.baseUrl) }
    var login by rememberSaveable { mutableStateOf(stored.login) }
    var password by rememberSaveable { mutableStateOf(stored.password) }
    var scopeSelection by rememberSaveable { mutableStateOf(stored.scope) }
    var statusText by remember { mutableStateOf("Статус: —") }
    var statusDetails by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    val sanitizedUrl = remember(baseUrl) { ApiClient.sanitizeBaseUrl(baseUrl) }

    fun saveAndTest() {
        context.saveConnection(ConnectionSettings(baseUrl, login, password, scopeSelection))
        coroutineScope.launch {
            try {
                isLoading = true
                val api: ApiService = ApiClient.create(sanitizedUrl)
                val full = api.healthFull()
                val status = full["status"] ?: "unknown"
                val checks = full["checks"] ?: emptyMap<String, Any>()
                statusText = "Health: $status"
                statusDetails = checks.toString()
            } catch (e: Exception) {
                statusText = "Ошибка: ${e.localizedMessage}"
                statusDetails = ""
            } finally {
                isLoading = false
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(text = "Подключение к NAS", fontWeight = FontWeight.Bold)
        OutlinedTextField(
            value = baseUrl,
            onValueChange = { baseUrl = it },
            label = { Text("Backend URL") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = login,
            onValueChange = { login = it },
            label = { Text("Логин") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Пароль") },
            modifier = Modifier.fillMaxWidth()
        )
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            ScopeRadio(value = "public", current = scopeSelection, onChange = { scopeSelection = it }, label = "Публичное хранилище")
            ScopeRadio(value = "private", current = scopeSelection, onChange = { scopeSelection = it }, label = "Приватное хранилище")
        }
        Button(onClick = { saveAndTest() }, modifier = Modifier.fillMaxWidth()) {
            Text(if (isLoading) "Проверяем..." else "Сохранить и проверить")
        }
        Text(text = statusText)
        if (statusDetails.isNotBlank()) {
            HorizontalDivider()
            Text(text = statusDetails)
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text(text = "Версия: ${BuildConfig.VERSION_NAME}")
    }
}

@Composable
private fun ScopeRadio(
    value: String,
    current: String,
    onChange: (String) -> Unit,
    label: String
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        RadioButton(selected = current == value, onClick = { onChange(value) })
        Text(label)
    }
}
