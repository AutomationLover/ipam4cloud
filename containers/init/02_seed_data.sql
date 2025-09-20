-- Insert default VRF
INSERT INTO vrf (vrf_id, description, is_default, routable_flag)
VALUES ('prod-vrf', 'Production VRF', TRUE, TRUE)
ON CONFLICT (vrf_id) DO NOTHING;

-- Insert public VRF for public IP addresses
INSERT INTO vrf (vrf_id, description, is_default, routable_flag)
VALUES ('public-vrf', 'Public IP Address VRF', FALSE, TRUE)
ON CONFLICT (vrf_id) DO NOTHING;

