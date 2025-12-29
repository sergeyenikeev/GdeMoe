package com.gdemo.ui.screens.locations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import com.gdemo.data.model.LocationCreateRequest
import com.gdemo.data.model.LocationDto
import com.gdemo.data.model.LocationUpdateRequest
import com.gdemo.data.remote.ApiClient
import com.gdemo.util.AnalyticsLogger
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
    var newPhotoMediaId by remember { mutableStateOf("") }
    var newParentExpanded by remember { mutableStateOf(false) }
    var newParentSelection by remember { mutableStateOf<LocationDto?>(null) }
    var editingLocation by remember { mutableStateOf<LocationDto?>(null) }
    var editName by remember { mutableStateOf("") }
    var editPhotoMediaId by remember { mutableStateOf("") }
    var editParentExpanded by remember { mutableStateOf(false) }
    var editParentSelection by remember { mutableStateOf<LocationDto?>(null) }
    val scope = rememberCoroutineScope()

    suspend fun loadLocations() {
        try {
            locations = api.locations()
            status = "Locations: ${locations.size}"
        } catch (e: Exception) {
            status = "Failed to load locations: ${e.localizedMessage}"
        }
    }

    LaunchedEffect(Unit) {
        loadLocations()
    }

    fun createLocation() {
        scope.launch {
            val trimmedName = newName.trim()
            if (trimmedName.isBlank()) {
                status = "Location name is required"
                return@launch
            }
            try {
                val photoId = newPhotoMediaId.toIntOrNull()
                val created = api.createLocation(
                    LocationCreateRequest(
                        name = trimmedName,
                        workspace_id = 2,
                        kind = "other",
                        parent_id = newParentSelection?.id,
                        photo_media_id = photoId
                    )
                )
                locations = locations + created
                newName = ""
                newPhotoMediaId = ""
                newParentSelection = null
                status = "Location created"
                AnalyticsLogger.event(
                    "location_create",
                    mapOf("id" to created.id, "parentId" to created.parent_id, "photoMediaId" to photoId)
                )
            } catch (e: Exception) {
                status = "Failed to create location: ${e.localizedMessage}"
            }
        }
    }

    fun deleteLocation(id: Int) {
        scope.launch {
            try {
                api.deleteLocation(id)
                locations = locations.filterNot { it.id == id }
                itemsByLocation = itemsByLocation - id
                status = "Location deleted"
                AnalyticsLogger.event("location_delete", mapOf("id" to id))
            } catch (e: Exception) {
                status = "Failed to delete location: ${e.localizedMessage}"
            }
        }
    }

    fun loadItemsFor(locationId: Int) {
        scope.launch {
            try {
                val items = api.itemsByLocation(locationId)
                itemsByLocation = itemsByLocation + (locationId to items)
                status = "Loaded items for location $locationId"
            } catch (e: Exception) {
                status = "Failed to load items: ${e.localizedMessage}"
            }
        }
    }

    fun openEdit(location: LocationDto) {
        editingLocation = location
        editName = location.name
        editPhotoMediaId = location.photo_media_id?.toString() ?: ""
        editParentSelection = locations.firstOrNull { it.id == location.parent_id }
        editParentExpanded = false
    }

    fun saveEdit() {
        val target = editingLocation ?: return
        val trimmedName = editName.trim()
        if (trimmedName.isBlank()) {
            status = "Location name is required"
            return
        }
        scope.launch {
            try {
                val newParentId = editParentSelection?.id
                val parentChanged = newParentId != target.parent_id
                val nameChanged = trimmedName != target.name
                if (nameChanged || (parentChanged && newParentId != null)) {
                    api.updateLocation(
                        target.id,
                        LocationUpdateRequest(
                            name = if (nameChanged) trimmedName else null,
                            parent_id = if (parentChanged && newParentId != null) newParentId else null
                        )
                    )
                }
                if (parentChanged && newParentId == null) {
                    api.clearLocationParent(target.id)
                }

                val newPhotoId = editPhotoMediaId.toIntOrNull()
                val photoChanged = newPhotoId != target.photo_media_id
                if (photoChanged) {
                    if (newPhotoId != null) {
                        api.setLocationPhoto(target.id, newPhotoId)
                    } else if (target.photo_media_id != null) {
                        api.clearLocationPhoto(target.id)
                    }
                }
                loadLocations()
                status = "Location updated"
                AnalyticsLogger.event(
                    "location_update",
                    mapOf("id" to target.id, "parentId" to newParentId, "photoMediaId" to newPhotoId)
                )
                editingLocation = null
            } catch (e: Exception) {
                status = "Failed to update location: ${e.localizedMessage}"
            }
        }
    }

    fun locationLabel(location: LocationDto): String {
        return location.path ?: location.name
    }

    LazyColumn(
        modifier = Modifier.padding(paddingValues).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { Text(status) }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Create location")
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text("Name") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Box {
                        OutlinedTextField(
                            value = newParentSelection?.let { locationLabel(it) } ?: "None",
                            onValueChange = {},
                            label = { Text("Parent") },
                            modifier = Modifier.fillMaxWidth(),
                            readOnly = true
                        )
                        DropdownMenu(
                            expanded = newParentExpanded,
                            onDismissRequest = { newParentExpanded = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("None") },
                                onClick = {
                                    newParentSelection = null
                                    newParentExpanded = false
                                }
                            )
                            locations.forEach { loc ->
                                DropdownMenuItem(
                                    text = { Text(locationLabel(loc)) },
                                    onClick = {
                                        newParentSelection = loc
                                        newParentExpanded = false
                                    }
                                )
                            }
                        }
                    }
                    Button(
                        onClick = { newParentExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Select parent")
                    }
                    OutlinedTextField(
                        value = newPhotoMediaId,
                        onValueChange = { newPhotoMediaId = it },
                        label = { Text("Photo media ID (optional)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(onClick = { createLocation() }, modifier = Modifier.fillMaxWidth()) {
                        Text("Create")
                    }
                }
            }
        }
        items(locations) { loc ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("ID ${loc.id}: ${loc.name}")
                    Text("Parent: ${loc.parent_id ?: "-"}  Path: ${loc.path ?: "-"}")
                    Text("Photo media: ${loc.photo_media_id ?: "-"}")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { loadItemsFor(loc.id) }) { Text("Load items") }
                        Button(onClick = { openEdit(loc) }) { Text("Edit") }
                        Button(onClick = { deleteLocation(loc.id) }) { Text("Delete") }
                    }
                    itemsByLocation[loc.id]?.let { items ->
                        if (items.isEmpty()) {
                            Text("No items")
                        } else {
                            items.forEach { item ->
                                Text("- ${item.title} (${item.status})")
                            }
                        }
                    }
                }
            }
        }
    }

    if (editingLocation != null) {
        AlertDialog(
            onDismissRequest = { editingLocation = null },
            confirmButton = {
                Button(onClick = { saveEdit() }) { Text("Save") }
            },
            title = { Text("Edit location") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = editName,
                        onValueChange = { editName = it },
                        label = { Text("Name") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Box {
                        OutlinedTextField(
                            value = editParentSelection?.let { locationLabel(it) } ?: "None",
                            onValueChange = {},
                            label = { Text("Parent") },
                            modifier = Modifier.fillMaxWidth(),
                            readOnly = true
                        )
                        DropdownMenu(
                            expanded = editParentExpanded,
                            onDismissRequest = { editParentExpanded = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("None") },
                                onClick = {
                                    editParentSelection = null
                                    editParentExpanded = false
                                }
                            )
                            locations.filter { it.id != editingLocation?.id }.forEach { loc ->
                                DropdownMenuItem(
                                    text = { Text(locationLabel(loc)) },
                                    onClick = {
                                        editParentSelection = loc
                                        editParentExpanded = false
                                    }
                                )
                            }
                        }
                    }
                    Button(
                        onClick = { editParentExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Select parent")
                    }
                    OutlinedTextField(
                        value = editPhotoMediaId,
                        onValueChange = { editPhotoMediaId = it },
                        label = { Text("Photo media ID") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        )
    }
}
