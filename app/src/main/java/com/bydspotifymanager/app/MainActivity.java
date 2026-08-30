package com.bydspotifymanager.app;

import android.app.Activity;
import android.content.*;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.text.InputFilter;
import android.view.View;
import android.widget.*;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.switchmaterial.SwitchMaterial;

import java.io.*;
import java.security.MessageDigest;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** BYD Spotify Manager for Spotify 9.1 and 8.9. */
public class MainActivity extends AppCompatActivity {
    private TextView txtOfficial, txtPrimary, txtSecondary, txtSourceStatus, txtProgress;
    private TextView txtOptimiseHint, txtSelectedSlotTitle, txtManagerVersion, txtIconHue;
    private TextView txtProgressStage, txtProgressPercent, txtSourceVersion, txtSlotsVersion, txtBrandingHint;
    private ProgressBar progressBar;

    private RadioButton radioEngine91, radioEngine89;
    private RadioButton radioPrimary, radioSecondary;
    private RadioButton radioScale100, radioScale120, radioScale140, radioScale160;
    private RadioButton radioPlayerLhs, radioPlayerRhs;
    private RadioButton radio89FontStock, radio89FontModerate, radio89FontLarge;
    private RadioButton radio89PanelLeft, radio89PanelRight;

    private EditText editAppName;
    private SwitchMaterial switchOptimise, switchBydLayout, switchAutoResume, switchIconBadge, switch89PreventPortrait;
    private Button btnPatchInstall, btnPrimaryInfo, btnSecondaryInfo;
    private SeekBar seekIconHue;
    private ImageView imgIconPreview;
    private View slotPrimaryCard, slotSecondaryCard, panel91, panel89;

    private android.graphics.Bitmap stockIconPreview, renderedIconPreview;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private SharedPreferences prefs;
    private boolean installReceiverRegistered;
    private boolean loadingSlotUi;
    private boolean engine89;
    private boolean sourceValid91;
    private boolean sourceValid89;
    private File sourceApk;

    private final BroadcastReceiver installRefreshReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            refreshPackages();
            int status = intent.getIntExtra("status", -999);
            String message = intent.getStringExtra("message");
            if (status == android.content.pm.PackageInstaller.STATUS_SUCCESS) {
                setBusy(false, "Spotify clone installed/updated successfully.");
                showProgress(100, "COMPLETE", "Spotify clone installed/updated successfully.");
            } else {
                String detail = (message == null || message.isEmpty())
                        ? "Android reported installation failure." : "Install result: " + message;
                setBusy(false, detail);
                showProgress(100, "INSTALL FAILED", detail);
            }
            if (prefs != null) {
                prefs.edit().remove("last_install_status").remove("last_install_message")
                        .remove("last_install_package").apply();
            }
        }
    };

    private final ActivityResultLauncher<Intent> pickApk = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(), result -> {
                if (result.getResultCode() != Activity.RESULT_OK || result.getData() == null) return;
                Uri uri = result.getData().getData();
                if (uri != null) importSource(uri);
            });

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        prefs = getSharedPreferences("manager_settings", MODE_PRIVATE);
        bind();
        setupActions();
        engine89 = "89".equals(prefs.getString("selected_engine", "91"));
        radioEngine89.setChecked(engine89);
        radioEngine91.setChecked(!engine89);
        radioPrimary.setChecked(true);
        radioSecondary.setChecked(false);
        applyEngineUi(false);
    }

    private void bind() {
        txtOfficial = findViewById(R.id.txtOfficial);
        txtPrimary = findViewById(R.id.txtPrimary);
        txtSecondary = findViewById(R.id.txtSecondary);
        txtSourceStatus = findViewById(R.id.txtSourceStatus);
        txtSourceVersion = findViewById(R.id.txtSourceVersion);
        txtSlotsVersion = findViewById(R.id.txtSlotsVersion);
        txtBrandingHint = findViewById(R.id.txtBrandingHint);
        txtProgress = findViewById(R.id.txtProgress);
        txtProgressStage = findViewById(R.id.txtProgressStage);
        txtProgressPercent = findViewById(R.id.txtProgressPercent);
        progressBar = findViewById(R.id.progressBar);
        txtOptimiseHint = findViewById(R.id.txtOptimiseHint);
        txtSelectedSlotTitle = findViewById(R.id.txtSelectedSlotTitle);
        txtManagerVersion = findViewById(R.id.txtManagerVersion);
        txtIconHue = findViewById(R.id.txtIconHue);
        if (txtManagerVersion != null) txtManagerVersion.setText("v" + BuildConfigData.MANAGER_VERSION);

        radioEngine91 = findViewById(R.id.radioEngine91);
        radioEngine89 = findViewById(R.id.radioEngine89);
        radioPrimary = findViewById(R.id.radioPrimary);
        radioSecondary = findViewById(R.id.radioSecondary);
        radioScale100 = findViewById(R.id.radioScale100);
        radioScale120 = findViewById(R.id.radioScale120);
        radioScale140 = findViewById(R.id.radioScale140);
        radioScale160 = findViewById(R.id.radioScale160);
        radioPlayerLhs = findViewById(R.id.radioPlayerLhs);
        radioPlayerRhs = findViewById(R.id.radioPlayerRhs);
        radio89FontStock = findViewById(R.id.radio89FontStock);
        radio89FontModerate = findViewById(R.id.radio89FontModerate);
        radio89FontLarge = findViewById(R.id.radio89FontLarge);
        radio89PanelLeft = findViewById(R.id.radio89PanelLeft);
        radio89PanelRight = findViewById(R.id.radio89PanelRight);

        editAppName = findViewById(R.id.editAppName);
        switchOptimise = findViewById(R.id.switchOptimise);
        switchBydLayout = findViewById(R.id.switchBydLayout);
        switchAutoResume = findViewById(R.id.switchAutoResume);
        switchIconBadge = findViewById(R.id.switchIconBadge);
        switch89PreventPortrait = findViewById(R.id.switch89PreventPortrait);
        seekIconHue = findViewById(R.id.seekIconHue);
        imgIconPreview = findViewById(R.id.imgIconPreview);

        btnPatchInstall = findViewById(R.id.btnPatchInstall);
        btnPrimaryInfo = findViewById(R.id.btnPrimaryInfo);
        btnSecondaryInfo = findViewById(R.id.btnSecondaryInfo);
        slotPrimaryCard = findViewById(R.id.slotPrimaryCard);
        slotSecondaryCard = findViewById(R.id.slotSecondaryCard);
        panel91 = findViewById(R.id.panel91);
        panel89 = findViewById(R.id.panel89);
    }

    private void setupActions() {
        findViewById(R.id.btnBrowse).setOnClickListener(v -> {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            i.setType("application/vnd.android.package-archive");
            i.addCategory(Intent.CATEGORY_OPENABLE);
            pickApk.launch(i);
        });
        findViewById(R.id.btnApkMirror).setOnClickListener(v ->
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(currentApkMirrorUrl()))));
        findViewById(R.id.btnRefresh).setOnClickListener(v -> {
            refreshPackages();
            validateStoredSource();
        });
        findViewById(R.id.btnDiagnostics).setOnClickListener(v -> copyDiagnostics());
        btnPrimaryInfo.setOnClickListener(v -> openAppInfo(currentPrimaryPackage()));
        btnSecondaryInfo.setOnClickListener(v -> openAppInfo(currentSecondaryPackage()));

        radioEngine91.setOnClickListener(v -> switchEngine(false));
        radioEngine89.setOnClickListener(v -> switchEngine(true));
        radioPrimary.setOnClickListener(v -> selectSlot(true));
        radioSecondary.setOnClickListener(v -> selectSlot(false));
        slotPrimaryCard.setOnClickListener(v -> selectSlot(true));
        slotSecondaryCard.setOnClickListener(v -> selectSlot(false));

        seekIconHue.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                txtIconHue.setText(progress + "°");
                updateIconPreview();
            }
            @Override public void onStartTrackingTouch(SeekBar seekBar) {}
            @Override public void onStopTrackingTouch(SeekBar seekBar) {}
        });
        switchIconBadge.setOnCheckedChangeListener((buttonView, isChecked) -> {
            if (!loadingSlotUi) updateIconPreview();
        });
        btnPatchInstall.setOnClickListener(v -> patchAndInstall());
    }

    private void switchEngine(boolean use89) {
        if (use89 == engine89) return;
        saveCurrentSlotUi();
        engine89 = use89;
        prefs.edit().putString("selected_engine", engine89 ? "89" : "91").apply();
        radioEngine89.setChecked(engine89);
        radioEngine91.setChecked(!engine89);
        applyEngineUi(true);
    }

    private void applyEngineUi(boolean resetProgress) {
        panel91.setVisibility(engine89 ? View.GONE : View.VISIBLE);
        panel89.setVisibility(engine89 ? View.VISIBLE : View.GONE);
        txtSlotsVersion.setText(engine89 ? "8.9" : "9.1");
        txtSourceVersion.setText(engine89 ? "Spotify " + BuildConfigData.V89_SUPPORTED_VERSION : "Spotify " + BuildConfigData.SUPPORTED_VERSION);
        txtBrandingHint.setText("0° = original Spotify colours.");
        editAppName.setFilters(new InputFilter[]{new InputFilter.LengthFilter(engine89 ? 24 : 32)});
        sourceApk = sourceFile(engine89);
        clearIconPreviews();
        selectSlot(radioSecondary.isChecked() ? false : true);
        refreshPackages();
        if (resetProgress) showProgress(0, "READY", "Switched to Spotify " + (engine89 ? "8.9" : "9.1") + ".");
        if (sourceApk.isFile()) validateStoredSource();
        else {
            setCurrentSourceValid(false);
            txtSourceStatus.setText("No source selected for Spotify " + (engine89 ? "8.9" : "9.1"));
            updateIconPreview();
        }
    }

    private void selectSlot(boolean primary) {
        radioPrimary.setChecked(primary);
        radioSecondary.setChecked(!primary);
        updateSlotUi();
    }

    private void updateSlotUi() {
        loadingSlotUi = true;
        boolean primary = radioPrimary.isChecked();
        if (engine89) {
            String prefix = primary ? "v89_primary" : "v89_secondary";
            String saved89Name = prefs.getString(prefix + "_name", primary ? "SpotifyPlus" : "SpotifyPlus2");
            if (primary && "SpotifyPlus8".equals(saved89Name)) saved89Name = "SpotifyPlus";
            if (!primary && "SpotifyPlus8-2".equals(saved89Name)) saved89Name = "SpotifyPlus2";
            editAppName.setText(saved89Name);
            String font = prefs.getString(prefix + "_font", "moderate");
            radio89FontStock.setChecked("stock".equals(font));
            radio89FontModerate.setChecked("moderate".equals(font));
            radio89FontLarge.setChecked("large".equals(font));
            String side = prefs.getString(prefix + "_panel", "right");
            radio89PanelLeft.setChecked("left".equals(side));
            radio89PanelRight.setChecked(!"left".equals(side));
            switch89PreventPortrait.setChecked(prefs.getBoolean(prefix + "_prevent_portrait", true));
            int hue = prefs.getInt(prefix + "_icon_hue", 0);
            boolean badge = prefs.getBoolean(prefix + "_icon_badge", false);
            seekIconHue.setProgress(IconBrandingUtil.normaliseHue(hue));
            txtIconHue.setText(IconBrandingUtil.normaliseHue(hue) + "°");
            switchIconBadge.setChecked(badge);
            txtSelectedSlotTitle.setText((primary ? "PRIMARY SETTINGS" : "SECONDARY SETTINGS") + " · SPOTIFY 8.9");
        } else {
            String prefix = primary ? "primary" : "secondary";
            editAppName.setText(prefs.getString(prefix + "_name", primary ? "SpotifyPlus" : "SpotifyPlus2"));
            String scale = prefs.getString(prefix + "_scale", "120");
            if ("150".equals(scale) || "135".equals(scale)) scale = "140";
            radioScale100.setChecked("100".equals(scale));
            radioScale120.setChecked("120".equals(scale));
            radioScale140.setChecked("140".equals(scale));
            radioScale160.setChecked("160".equals(scale));
            String playerSide = prefs.getString(prefix + "_player_side", "rhs");
            radioPlayerLhs.setChecked("lhs".equals(playerSide));
            radioPlayerRhs.setChecked(!"lhs".equals(playerSide));
            switchBydLayout.setChecked(prefs.getBoolean(prefix + "_byd_layout", true));
            switchOptimise.setChecked(prefs.getBoolean(prefix + "_optimise", true));
            switchAutoResume.setChecked(prefs.getBoolean(prefix + "_auto_resume", true));
            int hue = prefs.getInt(prefix + "_icon_hue", 0);
            boolean badge = prefs.getBoolean(prefix + "_icon_badge", false);
            seekIconHue.setProgress(IconBrandingUtil.normaliseHue(hue));
            txtIconHue.setText(IconBrandingUtil.normaliseHue(hue) + "°");
            switchIconBadge.setChecked(badge);
            txtOptimiseHint.setText("Installs matched DexMetadata for faster startup.");
            txtSelectedSlotTitle.setText((primary ? "PRIMARY SETTINGS" : "SECONDARY SETTINGS") + " · SPOTIFY 9.1");
        }
        loadingSlotUi = false;
        updateIconPreview();
        updatePatchButton();
    }

    private void saveCurrentSlotUi() {
        if (prefs == null || radioPrimary == null) return;
        boolean secondary = radioSecondary.isChecked();
        String appName = editAppName.getText().toString().trim();
        if (engine89) {
            String prefix = secondary ? "v89_secondary" : "v89_primary";
            prefs.edit()
                    .putString(prefix + "_name", appName)
                    .putString(prefix + "_font", selected89FontCode())
                    .putString(prefix + "_panel", radio89PanelLeft.isChecked() ? "left" : "right")
                    .putBoolean(prefix + "_prevent_portrait", switch89PreventPortrait.isChecked())
                    .putInt(prefix + "_icon_hue", seekIconHue.getProgress())
                    .putBoolean(prefix + "_icon_badge", switchIconBadge.isChecked())
                    .apply();
        } else {
            String prefix = secondary ? "secondary" : "primary";
            prefs.edit()
                    .putString(prefix + "_name", appName)
                    .putString(prefix + "_scale", selectedScaleCode())
                    .putBoolean(prefix + "_byd_layout", switchBydLayout.isChecked())
                    .putBoolean(prefix + "_optimise", switchOptimise.isChecked())
                    .putBoolean(prefix + "_auto_resume", switchAutoResume.isChecked())
                    .putString(prefix + "_player_side", radioPlayerLhs.isChecked() ? "lhs" : "rhs")
                    .putInt(prefix + "_icon_hue", seekIconHue.getProgress())
                    .putBoolean(prefix + "_icon_badge", switchIconBadge.isChecked())
                    .apply();
        }
    }

    private void clearIconPreviews() {
        if (renderedIconPreview != null && !renderedIconPreview.isRecycled()) renderedIconPreview.recycle();
        if (stockIconPreview != null && !stockIconPreview.isRecycled()) stockIconPreview.recycle();
        renderedIconPreview = null;
        stockIconPreview = null;
    }

    private void ensureStockIconPreview() {
        if (stockIconPreview == null && sourceApk != null && sourceApk.isFile()) {
            stockIconPreview = IconBrandingUtil.loadStockPreview(sourceApk);
        }
    }

    private void updateIconPreview() {
        if (imgIconPreview == null) return;
        ensureStockIconPreview();
        if (stockIconPreview != null) {
            android.graphics.Bitmap preview = engine89
                    ? Spotify89BrandingUtil.render(stockIconPreview, seekIconHue.getProgress(), switchIconBadge.isChecked())
                    : IconBrandingUtil.renderPreview(stockIconPreview, seekIconHue.getProgress(), switchIconBadge.isChecked());
            android.graphics.Bitmap oldPreview = renderedIconPreview;
            renderedIconPreview = preview;
            imgIconPreview.setImageBitmap(preview);
            if (oldPreview != null && oldPreview != stockIconPreview && oldPreview != preview && !oldPreview.isRecycled()) oldPreview.recycle();
            imgIconPreview.setAlpha(1f);
        } else {
            imgIconPreview.setImageResource(R.drawable.ic_manager);
            imgIconPreview.setAlpha(0.45f);
        }
    }

    private float selectedScaleFactor() {
        if (radioScale160.isChecked()) return 1.60f;
        if (radioScale140.isChecked()) return 1.40f;
        if (radioScale120.isChecked()) return 1.20f;
        return 1.00f;
    }

    private String selectedScaleCode() {
        if (radioScale160.isChecked()) return "160";
        if (radioScale140.isChecked()) return "140";
        if (radioScale120.isChecked()) return "120";
        return "100";
    }

    private String selected89FontCode() {
        if (radio89FontLarge.isChecked()) return "large";
        if (radio89FontStock.isChecked()) return "stock";
        return "moderate";
    }

    private Spotify89ResourceUtil.FontPreset selected89FontPreset() {
        if (radio89FontLarge.isChecked()) return Spotify89ResourceUtil.FontPreset.LARGE;
        if (radio89FontStock.isChecked()) return Spotify89ResourceUtil.FontPreset.STOCK;
        return Spotify89ResourceUtil.FontPreset.MODERATE;
    }

    private File sourceFile(boolean for89) {
        File dir = new File(getFilesDir(), "source");
        return new File(dir, for89 ? "spotify_8.9.76.538.apk" : "spotify_9.1.78.2215.apk");
    }

    private String currentPrimaryPackage() { return engine89 ? BuildConfigData.V89_PRIMARY_PACKAGE : BuildConfigData.PRIMARY_PACKAGE; }
    private String currentSecondaryPackage() { return engine89 ? BuildConfigData.V89_SECONDARY_PACKAGE : BuildConfigData.SECONDARY_PACKAGE; }
    private String currentTargetVersion() { return engine89 ? BuildConfigData.V89_SUPPORTED_VERSION : BuildConfigData.SUPPORTED_VERSION; }
    private long currentTargetVersionCode() { return engine89 ? BuildConfigData.V89_SUPPORTED_VERSION_CODE : BuildConfigData.SUPPORTED_VERSION_CODE; }
    private String currentApkMirrorUrl() { return engine89 ? BuildConfigData.V89_APKMIRROR_URL : BuildConfigData.APKMIRROR_URL; }
    private boolean currentSourceValid() { return engine89 ? sourceValid89 : sourceValid91; }
    private void setCurrentSourceValid(boolean valid) { if (engine89) sourceValid89 = valid; else sourceValid91 = valid; }
    private void setSourceValid(boolean for89, boolean valid) { if (for89) sourceValid89 = valid; else sourceValid91 = valid; }

    private void importSource(Uri uri) {
        final boolean for89 = engine89;
        final File target = sourceFile(for89);
        setBusy(true, "Copying selected Spotify APK…");
        showIndeterminate("VERIFYING SOURCE", "Copying and checking Spotify " + (for89 ? "8.9" : "9.1") + "…");
        worker.execute(() -> {
            try {
                File dir = target.getParentFile();
                if (!dir.exists() && !dir.mkdirs()) throw new IOException("Cannot create source directory");
                File tmp = new File(dir, for89 ? "source89.tmp" : "source91.tmp");
                try (InputStream in = getContentResolver().openInputStream(uri); OutputStream out = new FileOutputStream(tmp)) {
                    if (in == null) throw new IOException("Cannot read selected APK");
                    IoUtil.copy(in, out);
                }
                String detail;
                if (for89) {
                    ApkPatchEngine89.Validation validation = ApkPatchEngine89.validateSource(tmp);
                    if (!validation.ok) { tmp.delete(); throw new IllegalArgumentException(validation.detail); }
                    detail = "✓ " + validation.detail;
                } else {
                    String hash = IoUtil.sha256(tmp);
                    if (!BuildConfigData.STOCK_SHA256.equalsIgnoreCase(hash)) {
                        tmp.delete();
                        throw new IllegalArgumentException("Wrong APK. Expected exact Spotify " + BuildConfigData.SUPPORTED_VERSION + " build. SHA-256: " + hash);
                    }
                    detail = "✓ Verified original Spotify " + BuildConfigData.SUPPORTED_VERSION;
                }
                if (target.exists() && !target.delete()) throw new IOException("Cannot replace stored source APK");
                if (!tmp.renameTo(target)) throw new IOException("Cannot store selected source APK");
                setSourceValid(for89, true);
                runOnUiThread(() -> {
                    if (engine89 == for89) {
                        sourceApk = target;
                        txtSourceStatus.setText(detail);
                        clearIconPreviews();
                        updateIconPreview();
                        setBusy(false, "Source ready.");
                        showProgress(0, "READY", "Spotify " + (for89 ? "8.9" : "9.1") + " source verified. Ready to patch.");
                    }
                });
            } catch (Exception e) {
                setSourceValid(for89, false);
                runOnUiThread(() -> {
                    if (engine89 == for89) {
                        txtSourceStatus.setText("✕ " + e.getMessage());
                        clearIconPreviews();
                        updateIconPreview();
                        setBusy(false, "Source verification failed.");
                        showProgress(0, "SOURCE ERROR", "Source verification failed.");
                    }
                });
            }
        });
    }

    private void validateStoredSource() {
        final boolean for89 = engine89;
        final File target = sourceFile(for89);
        if (!target.isFile()) {
            setSourceValid(for89, false);
            if (engine89 == for89) txtSourceStatus.setText("No source selected for Spotify " + (for89 ? "8.9" : "9.1"));
            return;
        }
        worker.execute(() -> {
            boolean valid = false;
            String detail;
            try {
                if (for89) {
                    ApkPatchEngine89.Validation v = ApkPatchEngine89.validateSource(target);
                    valid = v.ok;
                    detail = v.ok ? "✓ Stored " + v.detail : "✕ " + v.detail;
                } else {
                    valid = BuildConfigData.STOCK_SHA256.equalsIgnoreCase(IoUtil.sha256(target));
                    detail = valid ? "✓ Stored original Spotify " + BuildConfigData.SUPPORTED_VERSION + " verified"
                            : "Stored source no longer matches supported Spotify 9.1 APK";
                }
            } catch (Exception e) {
                detail = "Source check failed: " + e.getMessage();
            }
            final boolean result = valid;
            final String message = detail;
            setSourceValid(for89, result);
            runOnUiThread(() -> {
                if (engine89 == for89) {
                    sourceApk = target;
                    txtSourceStatus.setText(message);
                    clearIconPreviews();
                    updateIconPreview();
                }
            });
        });
    }

    private void patchAndInstall() {
        String selectedPkg = radioSecondary.isChecked() ? currentSecondaryPackage() : currentPrimaryPackage();
        PackageInfo installedInfo = installedPackageInfo(selectedPkg);
        if (installedInfo != null && installedInfo.getLongVersionCode() > currentTargetVersionCode()) {
            // Android accepts an in-place update when the selected target has a higher
            // versionCode and is signed by the same Manager key (8.9 -> 9.1). Only the
            // reverse direction is a downgrade and therefore needs an uninstall first.
            showProfileDowngradeDialog(selectedPkg, installedInfo.versionName);
            return;
        }
        if (!currentSourceValid()) {
            Toast.makeText(this, "Select and verify the supported Spotify " + (engine89 ? "8.9" : "9.1") + " APK first.", Toast.LENGTH_LONG).show();
            return;
        }
        if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
            startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getPackageName())));
            Toast.makeText(this, "Allow installs from BYD Spotify Manager, then press Patch & Install again.", Toast.LENGTH_LONG).show();
            return;
        }
        saveCurrentSlotUi();
        if (engine89) patchAndInstall89(); else patchAndInstall91();
    }

    private void patchAndInstall91() {
        boolean secondary = radioSecondary.isChecked();
        boolean optimise = switchOptimise.isChecked();
        boolean bydLayout = switchBydLayout.isChecked();
        boolean autoResume = switchAutoResume.isChecked();
        boolean playerLeft = radioPlayerLhs.isChecked();
        int iconHue = seekIconHue.getProgress();
        boolean iconBadge = switchIconBadge.isChecked();
        String appName = editAppName.getText().toString().trim();
        if (appName.isEmpty()) appName = secondary ? "SpotifyPlus2" : "SpotifyPlus";
        String pkg = secondary ? BuildConfigData.SECONDARY_PACKAGE : BuildConfigData.PRIMARY_PACKAGE;
        float scaleFactor = selectedScaleFactor();
        final String finalAppName = appName;
        final File source = sourceFile(false);

        setBusy(true, "Starting Spotify 9.1 patch…");
        showProgress(5, "PREPARING", "Preparing a clean 9.1 build from the verified stock APK…");
        worker.execute(() -> {
            File work = new File(getCacheDir(), "build91");
            try {
                deleteTree(work);
                if (!work.mkdirs()) throw new IOException("Cannot create build directory");
                File unsigned = new File(work, "Spotify91_unsigned.apk");
                File signed = new File(work, "Spotify91_signed.apk");
                runOnUiThread(() -> showIndeterminate("PATCHING SPOTIFY 9.1", "Applying Spotify 9.1 settings…"));
                ApkPatchEngine.build(this, source, unsigned, secondary, finalAppName,
                        scaleFactor, bydLayout, playerLeft, autoResume, iconHue, iconBadge, this::postPatchDetail);
                showProgressFromWorker(76, "FINALISING APK", "Spotify 9.1 patch complete. Preparing signature…");
                showProgressFromWorker(82, "SIGNING", "Signing with this Manager installation's local key…");
                ApkSignerUtil.sign(unsigned, signed);
                showProgressFromWorker(88, "SIGNING", "APK signed and verified.");
                File dm = null;
                if (optimise) {
                    showProgressFromWorker(90, "OPTIMISING", "Creating matched DexMetadata…");
                    dm = new File(work, "base.dm");
                    ProfileMetadataUtil.createMatchingDm(this, signed, dm);
                    showProgressFromWorker(93, "OPTIMISING", "Matched DexMetadata attached.");
                } else {
                    showProgressFromWorker(93, "OPTIMISING", "Startup optimisation skipped.");
                }
                showProgressFromWorker(95, "STAGING INSTALL", "Opening the Android installer…");
                PackageInstallHelper.install(this, signed, dm, pkg);
                runOnUiThread(() -> showProgress(98, "INSTALLING", "Confirm the Android installation prompt if shown, then wait for installation to complete."));
            } catch (Exception e) { reportPatchFailure(e); }
        });
    }

    private void patchAndInstall89() {
        boolean secondary = radioSecondary.isChecked();
        Spotify89ResourceUtil.FontPreset fontPreset = selected89FontPreset();
        boolean rightPanel = radio89PanelRight.isChecked();
        boolean preventPortrait = switch89PreventPortrait.isChecked();
        int iconHue = seekIconHue.getProgress();
        boolean iconBadge = switchIconBadge.isChecked();
        String appName = editAppName.getText().toString().trim();
        if (appName.isEmpty()) appName = secondary ? "SpotifyPlus2" : "SpotifyPlus";
        String pkg = secondary ? BuildConfigData.V89_SECONDARY_PACKAGE : BuildConfigData.V89_PRIMARY_PACKAGE;
        final String finalAppName = appName;
        final File source = sourceFile(true);

        setBusy(true, "Starting Spotify 8.9 patch…");
        showProgress(5, "PREPARING", "Preparing Spotify 8.9 build…");
        worker.execute(() -> {
            File work = new File(getCacheDir(), "build89");
            try {
                deleteTree(work);
                if (!work.mkdirs()) throw new IOException("Cannot create 8.9 build directory");
                File unsigned = new File(work, "Spotify89_unsigned.apk");
                File signed = new File(work, "Spotify89_signed.apk");
                runOnUiThread(() -> showIndeterminate("PATCHING SPOTIFY 8.9", "Applying Spotify 8.9 settings…"));
                ApkPatchEngine89.build(this, source, unsigned, secondary, finalAppName,
                        fontPreset, rightPanel, preventPortrait, iconHue, iconBadge, this::postPatchDetail);
                showProgressFromWorker(78, "FINALISING APK", "Spotify 8.9 patch complete. Preparing signature…");
                showProgressFromWorker(84, "SIGNING", "Signing with this Manager installation's local key…");
                ApkSignerUtil.sign(unsigned, signed);
                showProgressFromWorker(91, "SIGNING", "Spotify 8.9 APK signed and verified.");
                showProgressFromWorker(95, "STAGING INSTALL", "Opening the Android installer…");
                PackageInstallHelper.install(this, signed, null, pkg);
                runOnUiThread(() -> showProgress(98, "INSTALLING", "Confirm the Android installation prompt if shown, then wait for installation to complete."));
            } catch (Exception e) { reportPatchFailure(e); }
        });
    }

    private void reportPatchFailure(Exception e) {
        runOnUiThread(() -> {
            String detail = "Patch failed: " + e.getClass().getSimpleName() + " · " + e.getMessage();
            setBusy(false, detail);
            showProgress(0, "PATCH FAILED", detail);
            Toast.makeText(this, "Patch failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
        });
    }

    private void postPatchDetail(String message) {
        runOnUiThread(() -> {
            if (progressBar != null) progressBar.setIndeterminate(true);
            if (txtProgressStage != null) txtProgressStage.setText(engine89 ? "PATCHING SPOTIFY 8.9" : "PATCHING SPOTIFY 9.1");
            if (txtProgressPercent != null) txtProgressPercent.setText("…");
            if (txtProgress != null) txtProgress.setText(message);
        });
    }

    private void showProgressFromWorker(int percent, String stage, String message) { runOnUiThread(() -> showProgress(percent, stage, message)); }

    private void showProgress(int percent, String stage, String message) {
        int value = Math.max(0, Math.min(100, percent));
        if (progressBar != null) { progressBar.setIndeterminate(false); progressBar.setProgress(value); }
        if (txtProgressStage != null) txtProgressStage.setText(stage);
        if (txtProgressPercent != null) txtProgressPercent.setText(value + "%");
        if (txtProgress != null) txtProgress.setText(message);
    }

    private void showIndeterminate(String stage, String message) {
        if (progressBar != null) progressBar.setIndeterminate(true);
        if (txtProgressStage != null) txtProgressStage.setText(stage);
        if (txtProgressPercent != null) txtProgressPercent.setText("…");
        if (txtProgress != null) txtProgress.setText(message);
    }

    private void consumePersistedInstallResult() {
        if (prefs == null || !prefs.contains("last_install_status")) return;
        int status = prefs.getInt("last_install_status", -999);
        String message = prefs.getString("last_install_message", "");
        prefs.edit().remove("last_install_status").remove("last_install_message").remove("last_install_package").apply();
        if (status == android.content.pm.PackageInstaller.STATUS_SUCCESS) {
            setBusy(false, "Spotify clone installed/updated successfully.");
            showProgress(100, "COMPLETE", "Spotify clone installed/updated successfully.");
        } else {
            String detail = message == null || message.isEmpty() ? "Android reported installation failure." : "Install result: " + message;
            setBusy(false, detail);
            showProgress(100, "INSTALL FAILED", detail);
        }
    }

    private void refreshPackages() {
        txtOfficial.setText(slotStatus(BuildConfigData.OFFICIAL_PACKAGE, true));
        txtPrimary.setText(slotStatus(currentPrimaryPackage(), false));
        txtSecondary.setText(slotStatus(currentSecondaryPackage(), false));
        btnPrimaryInfo.setEnabled(isInstalled(currentPrimaryPackage()));
        btnSecondaryInfo.setEnabled(isInstalled(currentSecondaryPackage()));
        updatePatchButton();
    }

    private void updatePatchButton() {
        if (btnPatchInstall == null) return;
        String pkg = radioSecondary != null && radioSecondary.isChecked() ? currentSecondaryPackage() : currentPrimaryPackage();
        PackageInfo installed = installedPackageInfo(pkg);
        if (installed == null) {
            btnPatchInstall.setText("PATCH & INSTALL");
            return;
        }

        long installedCode = installed.getLongVersionCode();
        long targetCode = currentTargetVersionCode();
        if (installedCode == targetCode) {
            btnPatchInstall.setText("APPLY CHANGES");
        } else if (installedCode < targetCode) {
            // Normal Android update path. In particular, Spotify 8.9 -> 9.1 keeps
            // the same package/signing identity and can upgrade in place.
            btnPatchInstall.setText("UPGRADE SLOT TO " + (engine89 ? "8.9" : "9.1"));
        } else {
            btnPatchInstall.setText("SWITCH SLOT TO " + (engine89 ? "8.9" : "9.1"));
        }
    }

    private PackageInfo installedPackageInfo(String pkg) {
        try { return getPackageManager().getPackageInfo(pkg, 0); }
        catch (Exception e) { return null; }
    }

    private String installedVersion(String pkg) {
        PackageInfo pi = installedPackageInfo(pkg);
        return pi == null ? null : pi.versionName;
    }

    private void showProfileDowngradeDialog(String pkg, String installedVersion) {
        String target = engine89 ? "Spotify 8.9" : "Spotify 9.1";
        String slot = radioSecondary.isChecked() ? "Secondary" : "Primary";
        new android.app.AlertDialog.Builder(this)
                .setTitle("Switch " + slot + " slot to " + target + "?")
                .setMessage(slot + " currently contains Spotify " + installedVersion + " at " + pkg + ".\n\n"
                        + "This change goes to an older Spotify version. Android does not allow a normal in-place downgrade, so the current app must be uninstalled first. App data for this slot will be removed.\n\n"
                        + "Upgrading in the other direction (8.9 -> 9.1) is supported in place and does not require this uninstall step.\n\n"
                        + "After uninstalling, return here and press Patch & Install again.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Uninstall current", (d, which) -> {
                    try { startActivity(new Intent(Intent.ACTION_DELETE, Uri.parse("package:" + pkg))); }
                    catch (Exception e) { Toast.makeText(this, "Cannot open Android uninstall screen.", Toast.LENGTH_LONG).show(); }
                })
                .show();
    }

    private boolean isInstalled(String pkg) {
        try { getPackageManager().getPackageInfo(pkg, 0); return true; }
        catch (Exception e) { return false; }
    }

    private String slotStatus(String pkg, boolean official) {
        try {
            PackageInfo pi = getPackageManager().getPackageInfo(pkg, 0);
            if (official) return "Installed · " + pi.versionName + "\n" + pkg;
            CharSequence label = pi.applicationInfo.loadLabel(getPackageManager());
            String shown = label == null ? "SpotifyPlus" : label.toString().trim();
            return shown + "\nInstalled · " + pi.versionName + "\n" + pkg;
        } catch (Exception e) { return "Not installed\n" + pkg; }
    }

    private String diagnosticStatus(String label, String pkg) {
        try { PackageInfo pi = getPackageManager().getPackageInfo(pkg, 0); return label + ": installed · " + pi.versionName + " · " + pkg; }
        catch (Exception e) { return label + ": not installed · " + pkg; }
    }

    private void openAppInfo(String pkg) {
        if (!isInstalled(pkg)) { Toast.makeText(this, "App is not installed.", Toast.LENGTH_SHORT).show(); return; }
        try { startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + pkg))); }
        catch (Exception e) { Toast.makeText(this, "Cannot open app info.", Toast.LENGTH_SHORT).show(); }
    }

    private void copyDiagnostics() {
        StringBuilder s = new StringBuilder();
        s.append("BYD Spotify Manager ").append(BuildConfigData.MANAGER_VERSION).append("\n")
                .append("Device: ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL).append("\n")
                .append("Android: ").append(Build.VERSION.RELEASE).append(" API ").append(Build.VERSION.SDK_INT).append("\n")
                .append("Selected Spotify version: ").append(engine89 ? BuildConfigData.V89_SUPPORTED_VERSION : BuildConfigData.SUPPORTED_VERSION).append("\n")
                .append("Source valid: ").append(currentSourceValid()).append("\n")
                .append(diagnosticStatus("Official", BuildConfigData.OFFICIAL_PACKAGE)).append("\n")
                .append(diagnosticStatus("Primary", currentPrimaryPackage())).append("\n")
                .append(diagnosticStatus("Secondary", currentSecondaryPackage())).append("\n")
                .append("Selected slot: ").append(radioPrimary.isChecked() ? "Primary" : "Secondary").append("\n");
        if (engine89) {
            s.append("8.9 font: ").append(selected89FontCode()).append("\n")
                    .append("8.9 side panel: ").append(radio89PanelLeft.isChecked() ? "Left/LHD" : "Right/RHD").append("\n")
                    .append("8.9 prevent portrait: ").append(switch89PreventPortrait.isChecked()).append("\n")
                    .append("8.9 auto-resume: enabled\n");
        } else {
            s.append("Email OTP login compatibility: forced ON\n")
                    .append("Performance optimisation: ").append(switchOptimise.isChecked()).append("\n")
                    .append("BYD wide-screen layout fixes: ").append(switchBydLayout.isChecked()).append("\n")
                    .append("Scale: ").append(selectedScaleCode()).append("% (from stock Spotify)\n")
                    .append("Player position: ").append(radioPlayerLhs.isChecked() ? "LHS" : "RHS").append("\n")
                    .append("Auto-resume: ").append(switchAutoResume.isChecked()).append("\n");
        }
        s.append("Icon hue: ").append(seekIconHue.getProgress()).append("° · + badge: ").append(switchIconBadge.isChecked()).append("\n");
        try {
            SigningKeyStore.KeyMaterial km = SigningKeyStore.getOrCreate();
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] fp = md.digest(km.certificate.getEncoded());
            StringBuilder f = new StringBuilder();
            for (byte b : fp) f.append(String.format("%02X", b));
            s.append("Local signing cert SHA-256: ").append(f).append("\n");
        } catch (Exception e) { s.append("Signing identity: unavailable\n"); }
        ClipboardManager cb = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        cb.setPrimaryClip(ClipData.newPlainText("BYD Spotify Manager diagnostics", s.toString()));
        Toast.makeText(this, "Diagnostic summary copied.", Toast.LENGTH_SHORT).show();
    }

    private void setBusy(boolean busy, String message) {
        btnPatchInstall.setEnabled(!busy);
        radioEngine91.setEnabled(!busy);
        radioEngine89.setEnabled(!busy);
        if (txtProgress != null) txtProgress.setText(message);
    }

    @Override protected void onStart() {
        super.onStart();
        if (!installReceiverRegistered) {
            IntentFilter filter = new IntentFilter(InstallResultReceiver.ACTION_INSTALL_FINISHED);
            if (Build.VERSION.SDK_INT >= 33) registerReceiver(installRefreshReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
            else registerReceiver(installRefreshReceiver, filter);
            installReceiverRegistered = true;
        }
    }

    @Override protected void onResume() {
        super.onResume();
        refreshPackages();
        consumePersistedInstallResult();
        mainHandler.postDelayed(this::refreshPackages, 400);
        mainHandler.postDelayed(this::refreshPackages, 1400);
    }

    @Override protected void onStop() {
        if (installReceiverRegistered) {
            try { unregisterReceiver(installRefreshReceiver); } catch (Exception ignored) {}
            installReceiverRegistered = false;
        }
        super.onStop();
    }

    private static void deleteTree(File f) {
        if (f == null || !f.exists()) return;
        if (f.isDirectory()) {
            File[] children = f.listFiles();
            if (children != null) for (File c : children) deleteTree(c);
        }
        f.delete();
    }

    @Override protected void onDestroy() {
        saveCurrentSlotUi();
        mainHandler.removeCallbacksAndMessages(null);
        worker.shutdownNow();
        clearIconPreviews();
        super.onDestroy();
    }
}
