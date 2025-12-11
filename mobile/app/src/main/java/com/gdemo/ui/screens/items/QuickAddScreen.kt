package com.gdemo.ui.screens.items

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.clickable
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.CreateItemRequest
import com.gdemo.data.model.LocationDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.util.AnalyticsLogger
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun QuickAddScreen(paddingValues: PaddingValues, onItemCreated: (Int) -> Unit = {}) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    var baseUrl by remember { mutableStateOf(stored.baseUrl) }
    var title by remember { mutableStateOf("") }
    var locations by remember { mutableStateOf<List<LocationDto>>(emptyList()) }
    var selectedLocation by remember { mutableStateOf<LocationDto?>(null) }
    var message by remember { mutableStateOf("") }
    var saveAndNext by remember { mutableStateOf(false) }
    var showPicker by remember { mutableStateOf(false) }
    var search by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    val api = remember(baseUrl) { ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl)) }

    LaunchedEffect(baseUrl) {
        runCatching { api.locations() }.onSuccess {
            locations = it
            AnalyticsLogger.debug("locations_loaded", mapOf("count" to it.size))
        }
    }

    fun save() {
        scope.launch {
            try {
                AnalyticsLogger.event("quick_add_submit", mapOf("location" to selectedLocation?.id))
                val created = api.createItem(
                    CreateItemRequest(
                        title = title,
                        status = "new",
                        workspace_id = 2,
                        location_id = selectedLocation?.id,
                        scope = stored.scope
                    )
                )
                message = "Создано #${created.id}"
                AnalyticsLogger.event("quick_add_success", mapOf("itemId" to created.id))
                onItemCreated(created.id)
                if (saveAndNext) {
                    title = ""
                } else {
                    title = ""
                    selectedLocation = null
                }
            } catch (e: Exception) {
                message = "Ошибка: ${e.localizedMessage}"
                AnalyticsLogger.event("quick_add_error", mapOf("error" to e.localizedMessage))
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
        Text("Быстрое добавление", style = MaterialTheme.typography.headlineSmall)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Название вещи") }
                )
                OutlinedButton(
                    onClick = {
                        showPicker = true
                        AnalyticsLogger.event("quick_add_open_location_picker")
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(selectedLocation?.path ?: "Выбрать локацию")
                }
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Checkbox(checked = saveAndNext, onCheckedChange = { saveAndNext = it })
                    Text("Сохранить и добавить следующую")
                }
                Button(
                    onClick = { save() },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = title.isNotBlank()
                ) { Text("Сохранить") }
                if (message.isNotBlank()) {
                    Text(message, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
    if (showPicker) {
        val filtered = locations.filter {
            search.isBlank() || it.name.contains(search, true) || (it.path?.contains(search, true) == true)
        }
        ModalBottomSheet(onDismissRequest = { showPicker = false }) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Выберите локацию", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = search,
                    onValueChange = { search = it },
                    label = { Text("Поиск по названию/пути") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))
                filtered.forEach { loc ->
                    ListItem(
                        headlineContent = { Text(loc.path ?: loc.name) },
                        supportingContent = { Text(loc.kind ?: "") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                selectedLocation = loc
                                showPicker = false
                                AnalyticsLogger.event("quick_add_location_selected", mapOf("locationId" to loc.id))
                            }
                    )
                }
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}
