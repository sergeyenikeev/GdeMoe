package com.gdemo.ui.navigation

import android.content.Context
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AdsClick
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.CreateItemRequest
import com.gdemo.data.model.ProductImportRequest
import com.gdemo.data.model.ReceiptImportResponse
import com.gdemo.data.model.SharedContent
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.remote.ApiService
import com.gdemo.ui.screens.items.ItemDetailsScreen
import com.gdemo.ui.screens.items.ItemListScreen
import com.gdemo.ui.screens.items.QuickAddScreen
import com.gdemo.ui.screens.locations.LocationTreeScreen
import com.gdemo.ui.screens.onboarding.OnboardingScreen
import com.gdemo.ui.screens.review.AiReviewScreen
import com.gdemo.ui.screens.review.AiReviewViewModel
import com.gdemo.ui.screens.settings.SettingsScreen
import com.gdemo.util.AnalyticsLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import androidx.core.net.toUri
import androidx.documentfile.provider.DocumentFile
import com.gdemo.ui.screens.search.SearchScreen
import okio.source

sealed class Destinations(val route: String, val label: String, val icon: @Composable (() -> Unit)) {
    object Onboarding : Destinations("onboarding", "Onboarding", { Icon(Icons.Default.Add, contentDescription = null) })
    object Items : Destinations("items", "Items", { Icon(Icons.Default.Home, contentDescription = null) })
    object Locations : Destinations("locations", "Locations", { Icon(Icons.Default.Search, contentDescription = null) })
    object Add : Destinations("quick_add", "Add", { Icon(Icons.Default.Add, contentDescription = null) })
    object AiReview : Destinations("ai_review", "AI", { Icon(Icons.Default.AdsClick, contentDescription = null) })
    object Settings : Destinations("settings", "Settings", { Icon(Icons.Default.Settings, contentDescription = null) })
    object ItemDetails : Destinations("item_details", "Details", { Icon(Icons.Default.Home, contentDescription = null) })
}

@Composable
fun GdeNavHost(isOnboarded: Boolean, onFinishOnboarding: () -> Unit, sharedContent: SharedContent? = null) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    var sharedHandled by remember { mutableStateOf(false) }
    val navController = rememberNavController()

    LaunchedEffect(sharedContent, stored.baseUrl, isOnboarded) {
        if (!sharedHandled && isOnboarded && sharedContent != null) {
            try {
                val api = ApiClient.create(ApiClient.sanitizeBaseUrl(stored.baseUrl))
                AnalyticsLogger.event("share_received", mapOf("type" to sharedContent.mimeType, "url" to sharedContent.url))
                if (!sharedContent.url.isNullOrBlank()) {
                    val sharedUrl = sharedContent.url
                    val imported = runCatching {
                        api.importProductLink(ProductImportRequest(url = sharedUrl, source = "mobile_share"))
                    }.getOrNull()
                    val attrs = mutableMapOf<String, Any?>()
                    imported?.attributes?.let { attrs.putAll(it) }
                    sharedContent.title?.takeIf { it.isNotBlank() }?.let { attrs.putIfAbsent("source_title", it) }
                    imported?.image_url?.let { attrs["image_url"] = it }
                    val links = mutableListOf<String>()
                    links.add(sharedUrl)
                    imported?.product_url?.let { if (!links.contains(it)) links.add(it) }
                    val created = api.createItem(
                        CreateItemRequest(
                            title = imported?.title ?: sharedContent.title ?: sharedUrl,
                            status = "new",
                            description = imported?.description,
                            scope = stored.scope,
                            price = imported?.price,
                            currency = imported?.currency,
                            store = sharedUrl.toUri().host,
                            attributes = attrs.ifEmpty { null },
                            links = links
                        )
                    )
                    val images = imported?.images ?: emptyList()
                    val targets = if (images.isNotEmpty()) images else imported?.image_url?.let { listOf(it) } ?: emptyList()
                    targets.take(2).forEach { imgUrl ->
                        attachImageFromUrl(api, stored.scope, created.id, imgUrl)
                    }
                    navController.navigate("${Destinations.ItemDetails.route}/${created.id}") {
                        launchSingleTop = true
                    }
                    AnalyticsLogger.event("share_import_success", mapOf("itemId" to created.id))
                } else if (!sharedContent.fileUri.isNullOrBlank()) {
                    val receiptItemId = handleReceiptShare(
                        api = api,
                        scope = stored.scope,
                        uri = sharedContent.fileUri,
                        mimeType = sharedContent.mimeType,
                        context = context
                    )
                    if (receiptItemId != null) {
                        navController.navigate("${Destinations.ItemDetails.route}/${receiptItemId}") {
                            launchSingleTop = true
                        }
                    }
                    AnalyticsLogger.event("share_receipt_success", mapOf("itemId" to receiptItemId))
                }
            } catch (_: Exception) {
                // ignore errors to avoid breaking host
                AnalyticsLogger.event("share_import_failed")
            } finally {
                sharedHandled = true
            }
        }
    }

    Scaffold(
        bottomBar = {
            val items = listOf(
                Destinations.Items,
                Destinations.Locations,
                Destinations.Add,
                Destinations.AiReview,
                Destinations.Settings
            )
            val navBackStackEntry by navController.currentBackStackEntryAsState()
            val currentRoute = navBackStackEntry?.destination?.route
            if (currentRoute != Destinations.Onboarding.route) {
                NavigationBar {
                    items.forEach { dest ->
                        NavigationBarItem(
                            icon = { dest.icon() },
                            label = null,
                            selected = currentRoute == dest.route,
                            onClick = {
                                navController.navigate(dest.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            }
                        )
                    }
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = if (isOnboarded) Destinations.Items.route else Destinations.Onboarding.route,
            modifier = Modifier.fillMaxSize()
        ) {
            composable(Destinations.Onboarding.route) {
                OnboardingScreen(onFinish = {
                    onFinishOnboarding()
                    navController.navigate(Destinations.Items.route) {
                        popUpTo(Destinations.Onboarding.route) { inclusive = true }
                    }
                })
            }
            composable(Destinations.Items.route) {
                AnalyticsLogger.screen("items")
                ItemListScreen(padding) { id ->
                    navController.navigate("${Destinations.ItemDetails.route}/$id")
                }
            }
            composable(Destinations.Locations.route) {
                AnalyticsLogger.screen("locations")
                LocationTreeScreen(padding)
            }
            composable(Destinations.Add.route) {
                AnalyticsLogger.screen("quick_add")
                QuickAddScreen(padding) { createdId ->
                    navController.navigate("${Destinations.ItemDetails.route}/$createdId") {
                        launchSingleTop = true
                    }
                }
            }
            composable(Destinations.AiReview.route) {
                AnalyticsLogger.screen("ai_review")
                val vm = remember(stored.baseUrl) { AiReviewViewModel(stored.baseUrl) }
                AiReviewScreen(
                    paddingValues = padding,
                    viewModel = vm,
                    baseUrl = stored.baseUrl,
                    onOpenItem = { id -> navController.navigate("${Destinations.ItemDetails.route}/$id") }
                )
            }
            composable(Destinations.Settings.route) {
                AnalyticsLogger.screen("settings")
                SettingsScreen(padding)
            }
            // optional search entry point (not on bottom bar)
            composable("search") {
                AnalyticsLogger.screen("search")
                SearchScreen(padding) { id ->
                    navController.navigate("${Destinations.ItemDetails.route}/$id")
                }
            }
            composable("${Destinations.ItemDetails.route}/{id}") { backStackEntry ->
                val id = backStackEntry.arguments?.getString("id") ?: ""
                ItemDetailsScreen(
                    itemId = id,
                    paddingValues = padding,
                    onDeleted = { navController.popBackStack() },
                    onBack = { navController.popBackStack() }
                )
            }
        }
    }
}

private suspend fun attachImageFromUrl(
    api: ApiService,
    scope: String,
    itemId: Int,
    imageUrl: String
) {
    withContext(Dispatchers.IO) {
        runCatching {
            val client = OkHttpClient.Builder().build()
            val request = Request.Builder().url(imageUrl).build()
            client.newCall(request).execute().use { resp ->
                if (!resp.isSuccessful) return@use
                val bodyBytes = resp.body?.bytes() ?: return@use
                val mime = resp.body?.contentType()?.toString() ?: "image/jpeg"
                val fileName = imageUrl.substringAfterLast('/').takeIf { it.isNotBlank() }
                    ?: "import_${System.currentTimeMillis()}.jpg"
                val reqBody = bodyBytes.toRequestBody(mime.toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", fileName, reqBody)
                val textBody: (String) -> okhttp3.RequestBody = {
                    it.toRequestBody("text/plain".toMediaTypeOrNull())
                }
                api.uploadMedia(
                    file = part,
                    workspaceId = textBody("2"),
                    ownerUserId = textBody("1"),
                    mediaType = textBody("photo"),
                    scope = textBody(scope),
                    subdir = textBody("items/$itemId"),
                    itemId = textBody(itemId.toString()),
                    analyze = textBody("true"),
                    source = textBody("import_url"),
                    clientCreatedAt = textBody(System.currentTimeMillis().toString()),
                    mimeType = textBody(mime)
                )
            }
        }
    }
}

private suspend fun handleReceiptShare(
    api: ApiService,
    scope: String,
    uri: String,
    mimeType: String?,
    context: Context
): Int? = withContext(Dispatchers.IO) {
    try {
        val contentUri = uri.toUri()
        val doc = DocumentFile.fromSingleUri(context, contentUri)
        val name = doc?.name ?: "receipt"
        val resolvedMime = mimeType ?: context.contentResolver.getType(contentUri) ?: "application/octet-stream"
        val body = object : okhttp3.RequestBody() {
            override fun contentType() = resolvedMime.toMediaTypeOrNull()
            override fun writeTo(sink: okio.BufferedSink) {
                context.contentResolver.openInputStream(contentUri)?.use { input ->
                    sink.writeAll(input.source())
                } ?: throw IllegalStateException("Cannot open shared file")
            }
        }
        val part = MultipartBody.Part.createFormData("file", name, body)
        val textBody: (String) -> okhttp3.RequestBody = { it.toRequestBody("text/plain".toMediaType()) }
        val imported: ReceiptImportResponse = api.importReceipt(
            file = part,
            workspaceId = textBody("2"),
            scope = textBody(scope)
        )
        val created = api.createItem(
            CreateItemRequest(
                title = imported.items.firstOrNull()?.name ?: imported.store ?: name,
                status = "new",
                description = imported.note ?: "Imported from receipt",
                scope = scope,
                links = listOfNotNull(imported.file_url),
                price = imported.total,
                currency = imported.currency,
                store = imported.store,
                purchase_datetime = imported.purchased_at
            )
        )
        created.id
    } catch (_: Exception) {
        null
    }
}
