"""Pre-QC rules for the synthetic-data demonstration."""


def consent_agent(source, basis):
    if source == "Synthetic" and basis == "Synthetic origin confirmed":
        return True, "Synthetic origin confirmed by operator."
    return False, "Confirm synthetic origin for every sample in this demo."


def governance_agent(local_use, identifiers):
    if local_use != "Approved" or identifiers != "None confirmed":
        return False, "Local research use and absence of personal identifiers require confirmation."
    return True, "Operator confirmed local research use and absence of personal identifiers."


def controls(ui):
    ui.caption("1. Consent Agent → 2. Data Governance Agent → 3. QC Agent")
    source = ui.selectbox("Dataset type", ["Select", "Synthetic", "Human or mixed", "Unknown"])
    basis = ui.selectbox("Consent basis for this demo", ["Select", "Synthetic origin confirmed", "Unresolved"])
    local = ui.selectbox("Local research processing approval", ["Select", "Approved", "Restricted"])
    identifiers = ui.selectbox("Personal identifiers in reads or metadata", ["Select", "None confirmed", "Present or unknown"])
    return source, basis, local, identifiers


def allow_qc(ui, settings):
    source, basis, local, identifiers = settings
    approved, reason = consent_agent(source, basis)
    if not approved:
        ui.warning("Consent Agent: HOLD. " + reason)
        ui.caption("Data Governance Agent: skipped. QC Agent: blocked.")
        return False
    ui.success("Consent Agent: cleared. " + reason)
    approved, reason = governance_agent(local, identifiers)
    if not approved:
        ui.warning("Data Governance Agent: HOLD. " + reason)
        ui.caption("QC Agent: blocked.")
        return False
    ui.success("Data Governance Agent: cleared. " + reason)
    ui.info("QC Agent: authorized to process this synthetic dataset.")
    return True
