package com.gdemo.ui.screens.locations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import androidx.compose.ui.unit.dp
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.Item
import com.gdemo.data.model.LocationDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.model.LocationCreateRequest
import kotlinx.coroutines.launch

@Composable
fun LocationTreeScreen(paddingValues: PaddingValues) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val stored = remember { context.loadConnection() }
    val api = remember { ApiClient.create(ApiClient.sanitizeBaseUrl(stored.baseUrl)) }
    var locations by remember { mutableStateOf<List<LocationDto>>(emptyList()) }
    var itemsByLocation by remember { mutableStateOf<Map<Int, List<Item>>>(emptyMap()) }
    var status by remember { mutableStateOf("") }
    var newName by remember { mutableStateOf("") }
    var newParent by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        try {
            locations = api.locations()
            status = "Мест: ${locations.size}"
        } catch (e: Exception) {
            status = "Ошибка загрузки мест: ${e.localizedMessage}"
        }
    }

    fun createLocation() {
        scope.launch {
            try {
                val body = LocationCreateRequest(
                    name = newName,
                    workspace_id = 2,
                    kind = "other",
                    parent_id = newParent.toIntOrNull()
                )
                val created = api.createLocation(body)
                locations = locations + created
                newName = ""
                newParent = ""
                status = "Место создано"
            } catch (e: Exception) {
                status = "Ошибка создания места: ${e.localizedMessage}"
            }
        }
    }

    fun deleteLocation(id: Int) {
        scope.launch {
            try {
                api.deleteLocation(id)
                locations = locations.filterNot { it.id == id }
                itemsByLocation = itemsByLocation - id
                status = "Место удалено"
            } catch (e: Exception) {
                status = "Ошибка удаления: ${e.localizedMessage}"
            }
        }
    }

    fun loadItemsFor(locationId: Int) {
        scope.launch {
            try {
                val items = api.itemsByLocation(locationId)
                itemsByLocation = itemsByLocation + (locationId to items)
                status = "Загружены предметы для $locationId"
            } catch (e: Exception) {
                status = "Ошибка загрузки предметов: ${e.localizedMessage}"
            }
        }
    }

    LazyColumn(
        modifier = Modifier.padding(paddingValues).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { Text(status) }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Добавить место")
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text("Название") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newParent,
                        onValueChange = { newParent = it },
                        label = { Text("Parent ID (опционально)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(onClick = { createLocation() }, modifier = Modifier.fillMaxWidth()) {
                        Text("Создать место")
                    }
                }
            }
        }
        items(locations) { loc ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("ID ${loc.id}: ${loc.name}")
                    Text("Родитель: ${loc.parent_id ?: "-"}  Путь: ${loc.path ?: "-"}")
                    Button(onClick = { loadItemsFor(loc.id) }) { Text("Показать предметы") }
                    Button(onClick = { deleteLocation(loc.id) }) { Text("Удалить место") }
                    itemsByLocation[loc.id]?.let { items ->
                        if (items.isEmpty()) {
                            Text("Предметов нет")
                        } else {
                            items.forEach { item ->
                                Text("- ${item.title} (статус ${item.status})")
                            }
                        }
                    }
                }
            }
        }
    }
}
