# MarianMT Model Training GUI
# PowerShell GUI for training custom subtitle translation models

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create main form
$form = New-Object System.Windows.Forms.Form
$form.Text = "MarianMT Model Trainer"
$form.Size = New-Object System.Drawing.Size(800, 700)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

# Create tab control
$tabControl = New-Object System.Windows.Forms.TabControl
$tabControl.Location = New-Object System.Drawing.Point(10, 10)
$tabControl.Size = New-Object System.Drawing.Size(760, 640)

# Tab 1: Train Model
$tabTrain = New-Object System.Windows.Forms.TabPage
$tabTrain.Text = "Train Model"
$tabTrain.UseVisualStyleBackColor = $true

# Tab 2: Manage Models
$tabManage = New-Object System.Windows.Forms.TabPage
$tabManage.Text = "Manage Models"
$tabManage.UseVisualStyleBackColor = $true

$tabControl.Controls.Add($tabTrain)
$tabControl.Controls.Add($tabManage)

# ===== TAB 1: TRAIN MODEL =====

$y = 20

# Data Source Type
$labelDataSource = New-Object System.Windows.Forms.Label
$labelDataSource.Text = "Training Data Source:"
$labelDataSource.Location = New-Object System.Drawing.Point(20, $y)
$labelDataSource.Size = New-Object System.Drawing.Size(150, 20)
$tabTrain.Controls.Add($labelDataSource)

$radioSRT = New-Object System.Windows.Forms.RadioButton
$radioSRT.Text = "SRT File Pairs"
$radioSRT.Location = New-Object System.Drawing.Point(180, $y)
$radioSRT.Size = New-Object System.Drawing.Size(120, 20)
$radioSRT.Checked = $true
$tabTrain.Controls.Add($radioSRT)

$radioJSON = New-Object System.Windows.Forms.RadioButton
$radioJSON.Text = "JSON File"
$radioJSON.Location = New-Object System.Drawing.Point(320, $y)
$radioJSON.Size = New-Object System.Drawing.Size(100, 20)
$tabTrain.Controls.Add($radioJSON)

$y += 40

# Source Language
$labelSource = New-Object System.Windows.Forms.Label
$labelSource.Text = "Source Language:"
$labelSource.Location = New-Object System.Drawing.Point(20, $y)
$labelSource.Size = New-Object System.Drawing.Size(150, 20)
$tabTrain.Controls.Add($labelSource)

$textSource = New-Object System.Windows.Forms.TextBox
$textSource.Location = New-Object System.Drawing.Point(180, $y)
$textSource.Size = New-Object System.Drawing.Size(100, 20)
$textSource.Text = "en"
$tabTrain.Controls.Add($textSource)

$y += 30

# Target Language
$labelTarget = New-Object System.Windows.Forms.Label
$labelTarget.Text = "Target Language:"
$labelTarget.Location = New-Object System.Drawing.Point(20, $y)
$labelTarget.Size = New-Object System.Drawing.Size(150, 20)
$tabTrain.Controls.Add($labelTarget)

$textTarget = New-Object System.Windows.Forms.TextBox
$textTarget.Location = New-Object System.Drawing.Point(180, $y)
$textTarget.Size = New-Object System.Drawing.Size(100, 20)
$textTarget.Text = "hu"
$tabTrain.Controls.Add($textTarget)

$y += 30

# Genre
$labelGenre = New-Object System.Windows.Forms.Label
$labelGenre.Text = "Genre:"
$labelGenre.Location = New-Object System.Drawing.Point(20, $y)
$labelGenre.Size = New-Object System.Drawing.Size(150, 20)
$tabTrain.Controls.Add($labelGenre)

$comboGenre = New-Object System.Windows.Forms.ComboBox
$comboGenre.Location = New-Object System.Drawing.Point(180, $y)
$comboGenre.Size = New-Object System.Drawing.Size(200, 20)
$comboGenre.DropDownStyle = "DropDownList"
$comboGenre.Items.AddRange(@("general", "drama", "comedy", "action", "scifi", "documentary", "romance", "thriller", "horror"))
$comboGenre.SelectedIndex = 0
$tabTrain.Controls.Add($comboGenre)

$y += 40

# Source Files (for SRT mode)
$labelSourceFiles = New-Object System.Windows.Forms.Label
$labelSourceFiles.Text = "Source SRT Files:"
$labelSourceFiles.Location = New-Object System.Drawing.Point(20, $y)
$labelSourceFiles.Size = New-Object System.Drawing.Size(150, 20)
$tabTrain.Controls.Add($labelSourceFiles)

$listSourceFiles = New-Object System.Windows.Forms.ListBox
$listSourceFiles.Location = New-Object System.Drawing.Point(180, $y)
$listSourceFiles.Size = New-Object System.Drawing.Size(450, 80)
$tabTrain.Controls.Add($listSourceFiles)

$btnAddSource = New-Object System.Windows.Forms.Button
$btnAddSource.Text = "Add Files..."
$btnAddSource.Location = New-Object System.Drawing.Point(640, $y)
$btnAddSource.Size = New-Object System.Drawing.Size(90, 25)
$tabTrain.Controls.Add($btnAddSource)

$btnClearSource = New-Object System.Windows.Forms.Button
$btnClearSource.Text = "Clear"
$btnClearSource.Location = New-Object System.Drawing.Point(640, ($y + 30))
$btnClearSource.Size = New-Object System.Drawing.Size(90, 25)
$tabTrain.Controls.Add($btnClearSource)

$y += 90

# Target Files (for SRT mode)
$labelTargetFiles = New-Object System.Windows.Forms.Label
$labelTargetFiles.Text = "Target SRT Files:"
$labelTargetFiles.Location = New-Object System.Drawing.Point(20, $y)
$labelTargetFiles.Size = New-Object System.Drawing.Size(150, 20)
$tabTrain.Controls.Add($labelTargetFiles)

$listTargetFiles = New-Object System.Windows.Forms.ListBox
$listTargetFiles.Location = New-Object System.Drawing.Point(180, $y)
$listTargetFiles.Size = New-Object System.Drawing.Size(450, 80)
$tabTrain.Controls.Add($listTargetFiles)

$btnAddTarget = New-Object System.Windows.Forms.Button
$btnAddTarget.Text = "Add Files..."
$btnAddTarget.Location = New-Object System.Drawing.Point(640, $y)
$btnAddTarget.Size = New-Object System.Drawing.Size(90, 25)
$tabTrain.Controls.Add($btnAddTarget)

$btnClearTarget = New-Object System.Windows.Forms.Button
$btnClearTarget.Text = "Clear"
$btnClearTarget.Location = New-Object System.Drawing.Point(640, ($y + 30))
$btnClearTarget.Size = New-Object System.Drawing.Size(90, 25)
$tabTrain.Controls.Add($btnClearTarget)

$y += 90

# JSON File (for JSON mode)
$labelJSONFile = New-Object System.Windows.Forms.Label
$labelJSONFile.Text = "JSON File:"
$labelJSONFile.Location = New-Object System.Drawing.Point(20, $y)
$labelJSONFile.Size = New-Object System.Drawing.Size(150, 20)
$labelJSONFile.Visible = $false
$tabTrain.Controls.Add($labelJSONFile)

$textJSONFile = New-Object System.Windows.Forms.TextBox
$textJSONFile.Location = New-Object System.Drawing.Point(180, $y)
$textJSONFile.Size = New-Object System.Drawing.Size(450, 20)
$textJSONFile.Visible = $false
$tabTrain.Controls.Add($textJSONFile)

$btnBrowseJSON = New-Object System.Windows.Forms.Button
$btnBrowseJSON.Text = "Browse..."
$btnBrowseJSON.Location = New-Object System.Drawing.Point(640, $y)
$btnBrowseJSON.Size = New-Object System.Drawing.Size(90, 25)
$btnBrowseJSON.Visible = $false
$tabTrain.Controls.Add($btnBrowseJSON)

$y += 40

# Training Parameters
$groupParams = New-Object System.Windows.Forms.GroupBox
$groupParams.Text = "Training Parameters"
$groupParams.Location = New-Object System.Drawing.Point(20, $y)
$groupParams.Size = New-Object System.Drawing.Size(710, 100)
$tabTrain.Controls.Add($groupParams)

$labelEpochs = New-Object System.Windows.Forms.Label
$labelEpochs.Text = "Epochs:"
$labelEpochs.Location = New-Object System.Drawing.Point(20, 25)
$labelEpochs.Size = New-Object System.Drawing.Size(100, 20)
$groupParams.Controls.Add($labelEpochs)

$numEpochs = New-Object System.Windows.Forms.NumericUpDown
$numEpochs.Location = New-Object System.Drawing.Point(130, 25)
$numEpochs.Size = New-Object System.Drawing.Size(100, 20)
$numEpochs.Minimum = 1
$numEpochs.Maximum = 20
$numEpochs.Value = 3
$groupParams.Controls.Add($numEpochs)

$labelBatch = New-Object System.Windows.Forms.Label
$labelBatch.Text = "Batch Size:"
$labelBatch.Location = New-Object System.Drawing.Point(260, 25)
$labelBatch.Size = New-Object System.Drawing.Size(100, 20)
$groupParams.Controls.Add($labelBatch)

$numBatch = New-Object System.Windows.Forms.NumericUpDown
$numBatch.Location = New-Object System.Drawing.Point(370, 25)
$numBatch.Size = New-Object System.Drawing.Size(100, 20)
$numBatch.Minimum = 1
$numBatch.Maximum = 32
$numBatch.Value = 8
$groupParams.Controls.Add($numBatch)

$labelLR = New-Object System.Windows.Forms.Label
$labelLR.Text = "Learning Rate:"
$labelLR.Location = New-Object System.Drawing.Point(20, 60)
$labelLR.Size = New-Object System.Drawing.Size(100, 20)
$groupParams.Controls.Add($labelLR)

$textLR = New-Object System.Windows.Forms.TextBox
$textLR.Location = New-Object System.Drawing.Point(130, 60)
$textLR.Size = New-Object System.Drawing.Size(100, 20)
$textLR.Text = "0.00005"
$groupParams.Controls.Add($textLR)

$labelModelName = New-Object System.Windows.Forms.Label
$labelModelName.Text = "Model Name:"
$labelModelName.Location = New-Object System.Drawing.Point(260, 60)
$labelModelName.Size = New-Object System.Drawing.Size(100, 20)
$groupParams.Controls.Add($labelModelName)

$textModelName = New-Object System.Windows.Forms.TextBox
$textModelName.Location = New-Object System.Drawing.Point(370, 60)
$textModelName.Size = New-Object System.Drawing.Size(200, 20)
$textModelName.PlaceholderText = "Optional custom name"
$groupParams.Controls.Add($textModelName)

$y += 110

# Progress Log
$labelLog = New-Object System.Windows.Forms.Label
$labelLog.Text = "Training Log:"
$labelLog.Location = New-Object System.Drawing.Point(20, $y)
$labelLog.Size = New-Object System.Drawing.Size(100, 20)
$tabTrain.Controls.Add($labelLog)

$y += 25

$textLog = New-Object System.Windows.Forms.TextBox
$textLog.Location = New-Object System.Drawing.Point(20, $y)
$textLog.Size = New-Object System.Drawing.Size(710, 80)
$textLog.Multiline = $true
$textLog.ScrollBars = "Vertical"
$textLog.ReadOnly = $true
$tabTrain.Controls.Add($textLog)

$y += 90

# Start Training Button
$btnStartTraining = New-Object System.Windows.Forms.Button
$btnStartTraining.Text = "Start Training"
$btnStartTraining.Location = New-Object System.Drawing.Point(300, $y)
$btnStartTraining.Size = New-Object System.Drawing.Size(150, 35)
$btnStartTraining.Font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
$tabTrain.Controls.Add($btnStartTraining)

# ===== TAB 2: MANAGE MODELS =====

$y = 20

# Models List
$labelModels = New-Object System.Windows.Forms.Label
$labelModels.Text = "Trained Models:"
$labelModels.Location = New-Object System.Drawing.Point(20, $y)
$labelModels.Size = New-Object System.Drawing.Size(150, 20)
$tabManage.Controls.Add($labelModels)

$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = "Refresh"
$btnRefresh.Location = New-Object System.Drawing.Point(640, $y)
$btnRefresh.Size = New-Object System.Drawing.Size(90, 25)
$tabManage.Controls.Add($btnRefresh)

$y += 30

$listModels = New-Object System.Windows.Forms.ListBox
$listModels.Location = New-Object System.Drawing.Point(20, $y)
$listModels.Size = New-Object System.Drawing.Size(710, 200)
$tabManage.Controls.Add($listModels)

$y += 210

# Model Info
$labelInfo = New-Object System.Windows.Forms.Label
$labelInfo.Text = "Model Information:"
$labelInfo.Location = New-Object System.Drawing.Point(20, $y)
$labelInfo.Size = New-Object System.Drawing.Size(150, 20)
$tabManage.Controls.Add($labelInfo)

$y += 25

$textModelInfo = New-Object System.Windows.Forms.TextBox
$textModelInfo.Location = New-Object System.Drawing.Point(20, $y)
$textModelInfo.Size = New-Object System.Drawing.Size(710, 250)
$textModelInfo.Multiline = $true
$textModelInfo.ScrollBars = "Vertical"
$textModelInfo.ReadOnly = $true
$tabManage.Controls.Add($textModelInfo)

$y += 260

# Model Actions
$btnDeleteModel = New-Object System.Windows.Forms.Button
$btnDeleteModel.Text = "Delete Selected Model"
$btnDeleteModel.Location = New-Object System.Drawing.Point(300, $y)
$btnDeleteModel.Size = New-Object System.Drawing.Size(150, 30)
$btnDeleteModel.Enabled = $false
$tabManage.Controls.Add($btnDeleteModel)

# ===== EVENT HANDLERS =====

# Toggle between SRT and JSON mode
$radioSRT.Add_CheckedChanged({
    $visible = $radioSRT.Checked
    $labelSourceFiles.Visible = $visible
    $listSourceFiles.Visible = $visible
    $btnAddSource.Visible = $visible
    $btnClearSource.Visible = $visible
    $labelTargetFiles.Visible = $visible
    $listTargetFiles.Visible = $visible
    $btnAddTarget.Visible = $visible
    $btnClearTarget.Visible = $visible
    
    $labelJSONFile.Visible = -not $visible
    $textJSONFile.Visible = -not $visible
    $btnBrowseJSON.Visible = -not $visible
})

# Add source files
$btnAddSource.Add_Click({
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Filter = "SRT Files (*.srt)|*.srt|All Files (*.*)|*.*"
    $openFileDialog.Multiselect = $true
    $openFileDialog.Title = "Select Source SRT Files"
    
    if ($openFileDialog.ShowDialog() -eq "OK") {
        foreach ($file in $openFileDialog.FileNames) {
            $listSourceFiles.Items.Add($file)
        }
    }
})

# Clear source files
$btnClearSource.Add_Click({
    $listSourceFiles.Items.Clear()
})

# Add target files
$btnAddTarget.Add_Click({
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Filter = "SRT Files (*.srt)|*.srt|All Files (*.*)|*.*"
    $openFileDialog.Multiselect = $true
    $openFileDialog.Title = "Select Target SRT Files"
    
    if ($openFileDialog.ShowDialog() -eq "OK") {
        foreach ($file in $openFileDialog.FileNames) {
            $listTargetFiles.Items.Add($file)
        }
    }
})

# Clear target files
$btnClearTarget.Add_Click({
    $listTargetFiles.Items.Clear()
})

# Browse JSON file
$btnBrowseJSON.Add_Click({
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"
    $openFileDialog.Multiselect = $false
    $openFileDialog.Title = "Select JSON Training Data File"
    
    if ($openFileDialog.ShowDialog() -eq "OK") {
        $textJSONFile.Text = $openFileDialog.FileName
    }
})

# Start training
$btnStartTraining.Add_Click({
    $textLog.Clear()
    $textLog.AppendText("Starting training...`r`n")
    
    # Build command
    $pythonCmd = "python train_marian.py"
    
    if ($radioSRT.Checked) {
        # SRT mode
        if ($listSourceFiles.Items.Count -eq 0 -or $listTargetFiles.Items.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show("Please select source and target SRT files.", "Error", "OK", "Error")
            return
        }
        
        if ($listSourceFiles.Items.Count -ne $listTargetFiles.Items.Count) {
            [System.Windows.Forms.MessageBox]::Show("Number of source and target files must match.", "Error", "OK", "Error")
            return
        }
        
        $pythonCmd += " train-srt"
        
        # Add source files
        $pythonCmd += " --source-files"
        foreach ($file in $listSourceFiles.Items) {
            $pythonCmd += " `"$file`""
        }
        
        # Add target files
        $pythonCmd += " --target-files"
        foreach ($file in $listTargetFiles.Items) {
            $pythonCmd += " `"$file`""
        }
    } else {
        # JSON mode
        if ([string]::IsNullOrWhiteSpace($textJSONFile.Text) -or -not (Test-Path $textJSONFile.Text)) {
            [System.Windows.Forms.MessageBox]::Show("Please select a valid JSON file.", "Error", "OK", "Error")
            return
        }
        
        $pythonCmd += " train-json --json-file `"$($textJSONFile.Text)`""
    }
    
    # Add common parameters
    $pythonCmd += " --source $($textSource.Text)"
    $pythonCmd += " --target $($textTarget.Text)"
    $pythonCmd += " --genre $($comboGenre.SelectedItem)"
    $pythonCmd += " --epochs $($numEpochs.Value)"
    $pythonCmd += " --batch-size $($numBatch.Value)"
    $pythonCmd += " --learning-rate $($textLR.Text)"
    
    if (-not [string]::IsNullOrWhiteSpace($textModelName.Text)) {
        $pythonCmd += " --model-name `"$($textModelName.Text)`""
    }
    
    $textLog.AppendText("Command: $pythonCmd`r`n`r`n")
    
    # Disable button during training
    $btnStartTraining.Enabled = $false
    $btnStartTraining.Text = "Training..."
    
    # Execute command asynchronously
    try {
        $process = Start-Process -FilePath "python" -ArgumentList $pythonCmd.Substring(7) -NoNewWindow -RedirectStandardOutput "training_output.log" -RedirectStandardError "training_error.log" -PassThru
        
        # Wait for completion in background
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = 1000
        $timer.Add_Tick({
            if ($process.HasExited) {
                $timer.Stop()
                $btnStartTraining.Enabled = $true
                $btnStartTraining.Text = "Start Training"
                
                # Read output
                if (Test-Path "training_output.log") {
                    $output = Get-Content "training_output.log" -Raw
                    $textLog.AppendText($output)
                }
                
                if (Test-Path "training_error.log") {
                    $errors = Get-Content "training_error.log" -Raw
                    if ($errors) {
                        $textLog.AppendText("`r`nErrors:`r`n$errors")
                    }
                }
                
                if ($process.ExitCode -eq 0) {
                    $textLog.AppendText("`r`n✅ Training completed successfully!")
                    [System.Windows.Forms.MessageBox]::Show("Training completed successfully!", "Success", "OK", "Information")
                } else {
                    $textLog.AppendText("`r`n❌ Training failed. Check the log for details.")
                    [System.Windows.Forms.MessageBox]::Show("Training failed. Check the log for details.", "Error", "OK", "Error")
                }
            }
        })
        $timer.Start()
        
    } catch {
        $textLog.AppendText("`r`nError: $_`r`n")
        $btnStartTraining.Enabled = $true
        $btnStartTraining.Text = "Start Training"
        [System.Windows.Forms.MessageBox]::Show("Failed to start training: $_", "Error", "OK", "Error")
    }
})

# Refresh models list
function RefreshModelsList {
    $listModels.Items.Clear()
    $textModelInfo.Clear()
    
    try {
        $output = python train_marian.py list 2>&1
        
        # Parse output to extract model names
        $lines = $output -split "`n"
        foreach ($line in $lines) {
            if ($line -match "^📦\s+(.+)$") {
                $modelName = $matches[1].Trim()
                $listModels.Items.Add($modelName)
            }
        }
        
        if ($listModels.Items.Count -eq 0) {
            $textModelInfo.Text = "No trained models found."
        }
    } catch {
        $textModelInfo.Text = "Error loading models: $_"
    }
}

$btnRefresh.Add_Click({
    RefreshModelsList
})

# Model selection changed
$listModels.Add_SelectedIndexChanged({
    if ($listModels.SelectedItem) {
        $btnDeleteModel.Enabled = $true
        
        # Get model info
        try {
            $modelName = $listModels.SelectedItem
            $output = python train_marian.py info "$modelName" 2>&1
            $textModelInfo.Text = $output -join "`r`n"
        } catch {
            $textModelInfo.Text = "Error loading model info: $_"
        }
    } else {
        $btnDeleteModel.Enabled = $false
        $textModelInfo.Clear()
    }
})

# Delete model
$btnDeleteModel.Add_Click({
    if ($listModels.SelectedItem) {
        $modelName = $listModels.SelectedItem
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Are you sure you want to delete model '$modelName'?",
            "Confirm Delete",
            "YesNo",
            "Warning"
        )
        
        if ($result -eq "Yes") {
            try {
                $output = python train_marian.py delete "$modelName" --yes 2>&1
                [System.Windows.Forms.MessageBox]::Show("Model deleted successfully.", "Success", "OK", "Information")
                RefreshModelsList
            } catch {
                [System.Windows.Forms.MessageBox]::Show("Failed to delete model: $_", "Error", "OK", "Error")
            }
        }
    }
})

# Load initial models list
RefreshModelsList

# Add tab control to form
$form.Controls.Add($tabControl)

# Show form
$form.ShowDialog() | Out-Null
