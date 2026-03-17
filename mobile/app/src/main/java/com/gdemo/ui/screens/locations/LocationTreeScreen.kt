package com.gdemo.ui.screens.locations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
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
import coil.compose.AsyncImage
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.Item
import com.gdemo.data.model.LocationCreateRequest
import com.gdemo.data.model.LocationDto
import com.gdemo.data.model.LocationUpdateRequest
import com.gdemo.data.model.MediaDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.util.AnalyticsLogger
import kotlinx.coroutines.launch

@Composable
fun LocationTreeScreen(paddingValues: PaddingValues) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val stored = remember { context.loadConnection() }
    val api = remember { ApiClient.create(ApiClient.sanitizeBaseUrl(stored.baseUrl)) }
    val scopeSelection = remember { if (stored.scope.isBlank()) "private" else stored.scope }
    var locations by remember { mutableStateOf<List<LocationDto>>(emptyList()) }
    var itemsByLocation by remember { mutableStateOf<Map<Int, List<Item>>>(emptyMap()) }
    var recentMedia by remember { mutableStateOf<List<MediaDto>>(emptyList()) }
    var status by remember { mutableStateOf("") }
    var newName by remember { mutableStateOf("") }
    var newPhotoMediaId by remember { mutableStateOf<Int?>(null) }
    var newParentExpanded by remember { mutableStateOf(false) }
    var newParentSelection by remember { mutableStateOf<LocationDto?>(null) }
    var editingLocation by remember { mutableStateOf<LocationDto?>(null) }
    var editName by remember { mutableStateOf("") }
    var editPhotoMediaId by remember { mutableStateOf<Int?>(null) }
    var editParentExpanded by remember { mutableStateOf(false) }
    var editParentSelection by remember { mutableStateOf<LocationDto?>(null) }
    var showPhotoPicker by remember { mutableStateOf(false) }
    var photoPickerForEdit by remember { mutableStateOf(false) }
    var showVideoPicker by remember { mutableStateOf(false) }
    var videoPickerLocation by remember { mutableStateOf<LocationDto?>(null) }
    val scope = rememberCoroutineScope()

    suspend fun loadLocations() {
        try {
            locations = api.locations()
            status = "Locations: ${locations.size}"
        } catch (e: Exception) {
            status = "Failed to load locations: ${e.localizedMessage}"
        }
    }

    suspend fun loadRecentMedia() {
        try {
            recentMedia = api.recentMedia(scopeSelection)
        } catch (e: Exception) {
            status = "Failed to load media: ${e.localizedMessage}"
        }
    }

    LaunchedEffect(Unit) {
        loadLocations()
        loadRecentMedia()
    }

    fun createLocation() {
        scope.launch {
            val trimmedName = newName.trim()
            if (trimmedName.isBlank()) {
                status = "Location name is required"
                return@launch
            }
            try {
                val photoId = newPhotoMediaId
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
                newPhotoMediaId = null
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
        editPhotoMediaId = location.photo_media_id
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

                val newPhotoId = editPhotoMediaId
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

    fun mediaUrl(media: MediaDto): String {
        val base = ApiClient.sanitizeBaseUrl(stored.baseUrl).trimEnd('/')
        val rel = (media.thumb_url ?: media.file_url).trimStart('/')
        return "$base/$rel"
    }

    fun openVideoPicker(location: LocationDto) {
        videoPickerLocation = location
        showVideoPicker = true
        scope.launch { loadRecentMedia() }
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
                    val selectedNewMedia = newPhotoMediaId?.let { id ->
                        recentMedia.firstOrNull { it.id == id }
                    }
                    Text("Photo: ${selectedNewMedia?.id ?: "None"}")
                    selectedNewMedia?.let { media ->
                        AsyncImage(
                            model = mediaUrl(media),
                            contentDescription = null,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(140.dp)
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = {
                                photoPickerForEdit = false
                                showPhotoPicker = true
                                scope.launch { loadRecentMedia() }
                            },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Select photo")
                        }
                        Button(
                            onClick = { newPhotoMediaId = null },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Clear")
                        }
                    }
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
                        Button(onClick = { openVideoPicker(loc) }) { Text("Link video") }
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
                    val selectedEditMedia = editPhotoMediaId?.let { id ->
                        recentMedia.firstOrNull { it.id == id }
                    }
                    Text("Photo: ${selectedEditMedia?.id ?: editPhotoMediaId ?: "None"}")
                    selectedEditMedia?.let { media ->
                        AsyncImage(
                            model = mediaUrl(media),
                            contentDescription = null,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(140.dp)
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = {
                                photoPickerForEdit = true
                                showPhotoPicker = true
                                scope.launch { loadRecentMedia() }
                            },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Select photo")
                        }
                        Button(
                            onClick = { editPhotoMediaId = null },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Clear")
                        }
                    }
                    Button(
                        onClick = {
                            editingLocation?.let { openVideoPicker(it) }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Link video")
                    }
                }
            }
        )
    }

    if (showPhotoPicker) {
        val photoCandidates = recentMedia.filter { it.mime_type?.startsWith("image") == true }
        AlertDialog(
            onDismissRequest = { showPhotoPicker = false },
            confirmButton = {
                Button(onClick = { showPhotoPicker = false }) { Text("Close") }
            },
            title = { Text("Select photo") },
            text = {
                LazyColumn(
                    modifier = Modifier.heightIn(max = 360.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(photoCandidates) { media ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    if (photoPickerForEdit) {
                                        editPhotoMediaId = media.id
                                    } else {
                                        newPhotoMediaId = media.id
                                    }
                                    showPhotoPicker = false
                                    AnalyticsLogger.event(
                                        "location_photo_select",
                                        mapOf("mediaId" to media.id, "edit" to photoPickerForEdit)
                                    )
                                },
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            AsyncImage(
                                model = mediaUrl(media),
                                contentDescription = null,
                                modifier = Modifier.height(64.dp)
                            )
                            Column {
                                Text("ID ${media.id}")
                                Text(media.mime_type ?: "image")
                            }
                        }
                    }
                    if (photoCandidates.isEmpty()) {
                        item { Text("No photos found in recent media") }
                    }
                }
            }
        )
    }

    if (showVideoPicker) {
        val videoCandidates = recentMedia.filter { it.mime_type?.startsWith("video") == true }
        val target = videoPickerLocation
        AlertDialog(
            onDismissRequest = { showVideoPicker = false },
            confirmButton = {
                Button(onClick = { showVideoPicker = false }) { Text("Close") }
            },
            title = { Text("Select video") },
            text = {
                LazyColumn(
                    modifier = Modifier.heightIn(max = 360.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(videoCandidates) { media ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    val location = target
                                    if (location != null) {
                                        scope.launch {
                                            try {
                                                api.linkLocationMedia(location.id, media.id)
                                                status = "Video linked to location ${location.id}"
                                                AnalyticsLogger.event(
                                                    "location_video_link",
                                                    mapOf("locationId" to location.id, "mediaId" to media.id)
                                                )
                                            } catch (e: Exception) {
                                                status = "Failed to link video: ${e.localizedMessage}"
                                            }
                                        }
                                    }
                                    showVideoPicker = false
                                },
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            AsyncImage(
                                model = mediaUrl(media),
                                contentDescription = null,
                                modifier = Modifier.height(64.dp)
                            )
                            Column {
                                Text("ID ${media.id}")
                                Text(media.mime_type ?: "video")
                            }
                        }
                    }
                    if (videoCandidates.isEmpty()) {
                        item { Text("No videos found in recent media") }
                    }
                }
            }
        )
    }
}
