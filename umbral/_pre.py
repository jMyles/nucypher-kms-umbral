from umbral.curvebn import CurveBN
from umbral.config import default_params
from umbral.keys import UmbralPublicKey
from umbral.params import UmbralParameters


def prove_cfrag_correctness(cfrag: "CapsuleFrag",
                            kfrag: "KFrag",
                            capsule: "Capsule",
                            metadata: bytes = None,
                            params: UmbralParameters = None
                            ) -> "CorrectnessProof":
    params = params if params is not None else default_params()

    rk = kfrag._bn_key
    t = CurveBN.gen_rand(params.curve)
    ####
    ## Here are the formulaic constituents shared with `assess_cfrag_correctness`.
    ####
    e = capsule._point_e
    v = capsule._point_v

    e1 = cfrag._point_e1
    v1 = cfrag._point_v1

    u = params.u
    u1 = kfrag._point_commitment

    e2 = t * e
    v2 = t * v
    u2 = t * u

    hash_input = (e, e1, e2, v, v1, v2, u, u1, u2)
    if metadata is not None:
        hash_input += (metadata,)
    h = CurveBN.hash(*hash_input, params=params)
    ########

    z3 = t + h * rk

    cfrag.attach_proof(e2, v2, u1, u2, metadata=metadata, z3=z3, kfrag_signature=kfrag.signature)

    # Check correctness of original ciphertext (check nº 2) at the end
    # to avoid timing oracles
    if not capsule.verify(params):
        raise capsule.NotValid("Capsule verification failed.")


def assess_cfrag_correctness(cfrag,
                             capsule: "Capsule",
                             delegating_point,
                             signing_pubkey,
                             encrypting_point,
                             params: UmbralParameters = None):
    if cfrag.proof is None:
        raise cfrag.NoProofProvided
    params = params if params is not None else default_params()

    ####
    ## Here are the formulaic constituents shared with `prove_cfrag_correctness`.
    ####
    e = capsule._point_e
    v = capsule._point_v

    e1 = cfrag._point_e1
    v1 = cfrag._point_v1

    u = params.u
    u1 = cfrag.proof._point_kfrag_commitment

    e2 = cfrag.proof._point_e2
    v2 = cfrag.proof._point_v2
    u2 = cfrag.proof._point_kfrag_pok

    hash_input = (e, e1, e2, v, v1, v2, u, u1, u2)
    if cfrag.proof.metadata is not None:
        hash_input += (cfrag.proof.metadata,)
    h = CurveBN.hash(*hash_input, params=params)
    ########

    ni = cfrag._point_noninteractive
    xcoord = cfrag._point_xcoord
    kfrag_id = cfrag._kfrag_id

    kfrag_validity_message = bytes().join(
        bytes(material) for material in (kfrag_id, delegating_point, encrypting_point, u1, ni, xcoord))
    valid_kfrag_signature = cfrag.proof.kfrag_signature.verify(kfrag_validity_message, signing_pubkey)

    z3 = cfrag.proof.bn_sig
    correct_reencryption_of_e = z3 * e == e2 + (h * e1)

    correct_reencryption_of_v = z3 * v == v2 + (h * v1)

    correct_rk_commitment = z3 * u == u2 + (h * u1)

    return valid_kfrag_signature \
           & correct_reencryption_of_e \
           & correct_reencryption_of_v \
           & correct_rk_commitment


def verify_kfrag(kfrag,
                 delegating_point,
                 signing_pubkey,
                 encrypting_point,
                 params: UmbralParameters = None
                 ):
    params = params if params is not None else default_params()

    u = params.u

    id = kfrag._id
    key = kfrag._bn_key
    u1 = kfrag._point_commitment
    ni = kfrag._point_noninteractive
    xcoord = kfrag._point_xcoord

    #  We check that the commitment u1 is well-formed
    correct_commitment = u1 == key * u

    kfrag_validity_message = bytes().join(
        bytes(material) for material in (id, delegating_point, encrypting_point, u1, ni, xcoord))
    valid_kfrag_signature = kfrag.signature.verify(kfrag_validity_message, signing_pubkey)

    return correct_commitment & valid_kfrag_signature
