<?xml version="1.0" encoding="UTF-8"?>
<!--
  Stylesheet: buildNav.xsl
  Purpose:
    Normalize navigator XML documents that are used to generate the EDIROM
    navigation structure. The stylesheet ensures stable XML identifiers for
    navigation definitions, categories, and items while preserving the original
    document content and converting target URIs to the correct publication path.

  Inputs:
    - A navigator XML template or fragment containing navigatorDefinition,
      navigatorCategory, and navigatorItem nodes.
    - Parameters: $subDiv, $volSlug

  Output:
    - A normalized navigator XML document with stable IDs and volume/subdivision
      aware target URIs.
-->
<xsl:stylesheet xmlns:edirom="http://www.edirom.de/ns/1.3" 
    xmlns="http://www.edirom.de/ns/1.3"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    version="1.0">

    <xsl:output indent="yes" />
    <!-- Optional subdivision name used to keep navigator IDs unique within a volume. -->
    <xsl:param name="subDiv"></xsl:param>
    <!-- Volume slug used to build the final xmldb target path for navigator items. -->
    <xsl:param name="volSlug"></xsl:param>

    <!-- Default identity copy rule: keep text and attributes unchanged unless
         a more specific template handles the current node. -->
    <xsl:template match="@*|text()">
        <xsl:copy/>
    </xsl:template>

    <!-- Ignore processing instructions so the transformed output stays clean. -->
    <xsl:template match="processing-instruction()"/>

    <!-- Rewrite generic element nodes into the EDIROM namespace while keeping the
         child structure intact and dropping xml:id/sortNo from inherited copies. -->
    <xsl:template match="*">
        <xsl:element name="{local-name()}" namespace="http://www.edirom.de/ns/1.3">
            <xsl:apply-templates select="@*[name() != 'xml:id' and name() != 'sortNo']|node()"/>
        </xsl:element>
    </xsl:template>

    <!-- Ensure each navigatorDefinition receives a stable XML id, prefixed with the
         subdivision when a sub-volume is being generated. -->
    <xsl:template match="navigatorDefinition">
        <navigatorDefinition>
            <xsl:attribute name="xml:id">
            <xsl:choose>
                <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="concat($subDiv, '_navDef')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="'navDef'"/>
                </xsl:otherwise>
            </xsl:choose>
            </xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'xml:id']|node()"/>
        </navigatorDefinition>
    </xsl:template>

    <!-- Categories receive generated IDs that remain reproducible within the same
         subdivision, preventing collisions between multiple edition parts. -->
    <xsl:template match="navigatorCategory">
        <xsl:variable name="genId" select="generate-id()"/>
        <navigatorCategory>
            <xsl:attribute name="xml:id">
            <xsl:choose>
                <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="concat($subDiv, '_', $genId)"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="$genId"/>
                </xsl:otherwise>
            </xsl:choose>
            </xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'xml:id' and name() != 'sortNo']|node()"/>
        </navigatorCategory>
    </xsl:template>

    <!-- Each navigator item is assigned a unique id and a sort position. The
         targets attribute is rewritten to point to the correct xmldb location for
         the current volume and subdivision. -->
    <xsl:template match="navigatorItem">
        <xsl:variable name="itemPos" select="count(preceding-sibling::navigatorItem) + 1"/>
        <xsl:variable name="parentCatId" select="ancestor::navigatorCategory[1]/@xml:id"/>
        <navigatorItem>
            <xsl:attribute name="xml:id">
            <xsl:choose>
                <xsl:when test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="concat($subDiv, '_item_', generate-id())"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="concat('item_', generate-id())"/>
                </xsl:otherwise>
            </xsl:choose>
            </xsl:attribute>
            <xsl:attribute name="sortNo"><xsl:value-of select="$itemPos"/></xsl:attribute>
            <xsl:attribute name="targets">
                <xsl:text>xmldb:exist:///db/apps/edirom-content/</xsl:text>
                <xsl:if test="$volSlug and $volSlug != '' and $volSlug != 'None'">
                    <xsl:value-of select="$volSlug"/>
                    <xsl:text>/</xsl:text>
                </xsl:if>
                <xsl:if test="$subDiv and $subDiv != '' and $subDiv != 'None'">
                    <xsl:value-of select="$subDiv"/>
                    <xsl:text>/</xsl:text>
                </xsl:if>
                <xsl:value-of select="@targets"/>
            </xsl:attribute>
            <xsl:apply-templates select="@*[name() != 'targets']|node()"/>
        </navigatorItem>
    </xsl:template>
    
</xsl:stylesheet>